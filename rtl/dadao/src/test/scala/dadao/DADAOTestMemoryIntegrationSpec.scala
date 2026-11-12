package dadao

import chisel3._
import chiseltest._
import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

final class DADAOTestMemoryIntegrationSpec
    extends AnyFlatSpec
    with ChiselScalatestTester
    with Matchers {
  behavior of "DADAOCore with test memory"

  private val params = DADAOParams()
  private val testPc = BigInt("fc0000000000", 16)
  private val legacyExitBase = BigInt("ffff80000000", 16)

  private def loadEntry(
      dut: DADAOTestMemoryHarness,
      index: Int,
      address: BigInt,
      data: BigInt,
      writable: Boolean = true,
      fault: Boolean = false,
      faultCode: Int = 0,
      instruction: Boolean = true
  ): Unit = {
    val blockData = if (instruction) data << 32 else data
    dut.io.load.valid.poke(true.B)
    dut.io.load.index.poke(index.U)
    dut.io.load.address.poke(address.U)
    dut.io.load.data.poke(blockData.U)
    dut.io.load.writable.poke(writable.B)
    dut.io.load.fault.poke(fault.B)
    dut.io.load.faultCode.poke(faultCode.U)
    dut.clock.step()
    dut.io.load.valid.poke(false.B)
  }

  private def loadInstructionBeat(
      dut: DADAOTestMemoryHarness,
      index: Int,
      address: BigInt,
      firstWord: BigInt,
      secondWord: BigInt
  ): Unit = {
    loadEntry(
      dut,
      index,
      address,
      (firstWord << 32) | secondWord,
      instruction = false
    )
  }

  private def holdResetAt(
      dut: DADAOTestMemoryHarness,
      pc: BigInt
  ): Unit = {
    dut.io.testRegWrite.valid.poke(false.B)
    dut.io.testRegWrite.bank.poke(DADAORegBank.Rd.U)
    dut.io.testRegWrite.addr.poke(0.U)
    dut.io.testRegWrite.data.poke(0.U)
    dut.io.debugRegBank.poke(DADAORegBank.Rd.U)
    dut.io.debugRegAddr.poke(0.U)
    dut.io.testCfxWrite.valid.poke(false.B)
    dut.io.testCfxWrite.cfxha.poke(0.U)
    dut.io.testCfxWrite.cg.poke(0.U)
    dut.io.testCfxWrite.rc.poke(0.U)
    dut.io.testCfxWrite.data.poke(0.U)
    dut.io.testCfxStatusSet.valid.poke(false.B)
    dut.io.testCfxStatusSet.runMode.poke(DADAORunMode.Hypv.U)
    dut.io.testCfxStatusSet.cfxCode.poke(DADAOCfxCode.Power.U)
    dut.io.testCfxStatusSet.cfxMask.poke(
      BigInt("ffffffffffffffff", 16).U
    )
    dut.io.debugCfxRead.cfxha.poke(0.U)
    dut.io.debugCfxRead.cg.poke(0.U)
    dut.io.debugCfxRead.rc.poke(0.U)
    dut.io.pcInitValid.poke(true.B)
    dut.io.pcInit.poke(pc.U)
    dut.reset.poke(true.B)
    dut.clock.step(2)
    dut.reset.poke(false.B)
    dut.clock.step()
  }

  private def releasePcInit(dut: DADAOTestMemoryHarness): Unit = {
    dut.io.pcInitValid.poke(false.B)
    dut.clock.step()
  }

  private def encodeUInt(value: BigInt, width: Int): Array[Byte] = {
    Array.tabulate(width) { index =>
      val shift = (width - 1 - index) * 8
      ((value >> shift) & 0xff).toByte
    }
  }

  private def decodeUInt(bytes: Array[Byte]): BigInt = {
    bytes.foldLeft(BigInt(0)) { (value, byte) =>
      (value << 8) | BigInt(byte & 0xff)
    }
  }

  private def setField(
      word: BigInt,
      offset: Int,
      value: BigInt,
      width: Int = 6
  ): BigInt = {
    val mask = ((BigInt(1) << width) - 1) << offset
    (word & ~mask) | ((value << offset) & mask)
  }

  private def cfx2Word(
      id: String,
      cfxha: Int,
      cg: Int,
      rc: Int,
      rd: Int
  ): BigInt = {
    val base = DADAODecoderTable.entries(
      DADAODecoderTable.ids.indexOf(id)
    ).value
    setField(
      setField(
        setField(
          setField(base, 18, cfxha),
          12,
          cg
        ),
        6,
        rc
      ),
      0,
      rd
    )
  }

  private def cfxImmediateWord(
      id: String,
      cfxha: Int,
      immediate: BigInt
  ): BigInt = {
    val base = DADAODecoderTable.entries(
      DADAODecoderTable.ids.indexOf(id)
    ).value
    setField(
      setField(base, 18, cfxha),
      0,
      immediate,
      18
    )
  }

  private def writeCfx(
      dut: DADAOTestMemoryHarness,
      cfxha: Int,
      cg: Int,
      rc: Int,
      data: BigInt
  ): Unit = {
    dut.io.testCfxWrite.valid.poke(true.B)
    dut.io.testCfxWrite.cfxha.poke(cfxha.U)
    dut.io.testCfxWrite.cg.poke(cg.U)
    dut.io.testCfxWrite.rc.poke(rc.U)
    dut.io.testCfxWrite.data.poke(data.U)
    dut.clock.step()
    dut.io.testCfxWrite.valid.poke(false.B)
  }

  private def readCfx(
      dut: DADAOTestMemoryHarness,
      cfxha: Int,
      cg: Int,
      rc: Int
  ): BigInt = {
    dut.io.debugCfxRead.cfxha.poke(cfxha.U)
    dut.io.debugCfxRead.cg.poke(cg.U)
    dut.io.debugCfxRead.rc.poke(rc.U)
    dut.io.debugCfxReadValid.expect(true.B)
    dut.io.debugCfxReadData.peek().litValue
  }

  private def waitForPc(
      dut: DADAOTestMemoryHarness,
      expectedPc: BigInt,
      maxCycles: Int = 64
  ): Unit = {
    var cycles = 0
    while (
      dut.io.debugPc.peek().litValue != expectedPc &&
      cycles < maxCycles
    ) {
      dut.clock.step()
      cycles += 1
    }
    dut.io.debugPc.expect(expectedPc.U)
  }

  private def expectRegister(
      dut: DADAOTestMemoryHarness,
      bank: Int,
      address: Int,
      expected: BigInt
  ): Unit = {
    dut.io.debugRegBank.poke(bank.U)
    dut.io.debugRegAddr.poke(address.U)
    dut.clock.step()
    dut.io.debugRegData.expect(expected.U)
  }

  private def codedBlockInstruction(
      id: String,
      startReg: Int,
      baseReg: Int,
      offsetReg: Int,
      count: Int
  ): BigInt = {
    val index = DADAODecoderTable.ids.indexOf(id)
    val word = DADAODecoderTable.entries(index).value
    setField(
      setField(
        setField(
          setField(word, 18, startReg),
          12,
          baseReg
        ),
        6,
        offsetReg
      ),
      0,
      count
    )
  }

  private def loadRegister(
      dut: DADAOTestMemoryHarness,
      bank: Int,
      address: Int,
      value: BigInt
  ): Unit = {
    dut.io.testRegWrite.valid.poke(true.B)
    dut.io.testRegWrite.bank.poke(bank.U)
    dut.io.testRegWrite.addr.poke(address.U)
    dut.io.testRegWrite.data.poke(value.U)
    dut.clock.step()
    dut.io.testRegWrite.valid.poke(false.B)
  }

  private def checkStoreRoundTrip(
      storeId: String,
      sourceBank: Int,
      sourceReg: Int,
      registerValue: BigInt,
      loadId: String,
      expectedValue: BigInt,
      expectedWstrb: Int
  ): Unit = {
    test(
      new DADAOTestMemoryHarness(
        params,
        maxEntries = 16,
        reqReadyDelay = 1,
        memRespLatency = 2
      )
    ) { dut =>
      val storeEntryIndex = DADAODecoderTable.ids.indexOf(storeId)
      val storeBaseWord = DADAODecoderTable.entries(storeEntryIndex).value
      val storeWord = setField(
        setField(storeBaseWord, 18, sourceReg),
        12,
        2
      )

      val loadEntryIndex = DADAODecoderTable.ids.indexOf(loadId)
      val loadBaseWord = DADAODecoderTable.entries(loadEntryIndex).value
      val loadWord = setField(setField(loadBaseWord, 18, 3), 12, 2)
      val dataAddress = testPc + 0x100

      holdResetAt(dut, testPc)
      loadRegister(dut, sourceBank, sourceReg, registerValue)
      loadRegister(dut, DADAORegBank.Rb, 2, dataAddress)
      loadInstructionBeat(
        dut,
        0,
        testPc,
        storeWord,
        loadWord
      )
      loadEntry(
        dut,
        1,
        dataAddress,
        0,
        instruction = false
      )
      releasePcInit(dut)

      var cycles = 0
      var observedWriteData = BigInt(0)
      var observedWstrb = 0
      var observedStoreRequest = false
      while (
        dut.io.debugPc.peek().litValue != testPc + 8 &&
        cycles < 128
      ) {
        dut.clock.step()
        if (
          dut.io.debugDataRequestWrite.peek().litToBoolean &&
          dut.io.debugDataRequestAddr.peek().litValue == dataAddress
        ) {
          observedStoreRequest = true
          observedWriteData =
            dut.io.debugDataRequestWdata.peek().litValue
          observedWstrb =
            dut.io.debugDataRequestWstrb.peek().litValue.toInt
        }
        cycles += 1
      }

      dut.io.debugPc.expect((testPc + 8).U)
      dut.io.debugFault.expect(false.B)
      assert(observedStoreRequest, s"$storeId did not issue a write request")
      assert(
        observedWriteData == expectedValue,
        s"$storeId wrote $observedWriteData, expected $expectedValue"
      )
      assert(
        observedWstrb == expectedWstrb,
        s"$storeId used wstrb $observedWstrb, expected $expectedWstrb"
      )
      dut.io.debugRegBank.poke(DADAORegBank.Rd.U)
      dut.io.debugRegAddr.poke(3.U)
      dut.clock.step()
      dut.io.debugRegData.expect(expectedValue.U)
      dut.io.stats.writeCount.expect(1.U)
      assert(dut.io.stats.requestCount.peek().litValue >= 4)
    }
  }

  private def checkDataAccessFaultBeforeRequest(
      instructionId: String,
      sourceBank: Int,
      sourceReg: Int,
      sourceValue: BigInt,
      dataAddress: BigInt,
      expectedFaultCode: Int,
      isStore: Boolean
  ): Unit = {
    test(
      new DADAOTestMemoryHarness(
        params,
        maxEntries = 16,
        reqReadyDelay = 1,
        memRespLatency = 1
      )
    ) { dut =>
      val instructionIndex =
        DADAODecoderTable.ids.indexOf(instructionId)
      val baseWord =
        DADAODecoderTable.entries(instructionIndex).value
      val word = setField(
        setField(baseWord, 18, sourceReg),
        12,
        2
      )

      holdResetAt(dut, testPc)
      loadRegister(dut, sourceBank, sourceReg, sourceValue)
      loadRegister(dut, DADAORegBank.Rb, 2, dataAddress)
      loadEntry(dut, 0, testPc, word)
      releasePcInit(dut)

      var cycles = 0
      while (
        !dut.io.debugFault.peek().litToBoolean &&
        cycles < 64
      ) {
        dut.clock.step()
        cycles += 1
      }

      dut.io.debugFault.expect(true.B)
      dut.io.debugFaultCode.expect(expectedFaultCode.U)
      dut.io.debugFaultReason.expect(
        DADAODebugFaultReason.AccessFault.U
      )
      dut.io.debugPc.expect(testPc.U)
      dut.io.stats.requestCount.expect(1.U)
      if (isStore) {
        dut.io.stats.writeCount.expect(0.U)
      }
      if (!isStore) {
        dut.io.debugRegBank.poke(DADAORegBank.Rd.U)
        dut.io.debugRegAddr.poke(1.U)
        dut.clock.step()
        dut.io.debugRegData.expect(0.U)
      }
    }
  }

  it should "fetch and decode a program through the FSM memory model" in {
    test(
      new DADAOTestMemoryHarness(
        params,
        maxEntries = 16,
        reqReadyDelay = 2,
        memRespLatency = 4
      )
    ) { dut =>
      val swym = DADAODecoderTable.entries(DADAODecoderTable.swymId)
      holdResetAt(dut, testPc)
      loadEntry(dut, 0, testPc, swym.value)
      releasePcInit(dut)

      var cycles = 0
      while (
        dut.io.debugPc.peek().litValue != testPc + 4 &&
        cycles < 16
      ) {
        dut.clock.step()
        cycles += 1
      }

      dut.io.debugPc.expect((testPc + 4).U)
      dut.io.debugDecodedValid.expect(true.B)
      dut.io.debugNoop.expect(true.B)
      dut.io.debugFault.expect(false.B)
      assert(
        dut.io.stats.requestCount.peek().litValue >= 1,
        "core did not issue a fetch request"
      )
    }
  }

  it should "propagate a memory fault without advancing PC" in {
    test(
      new DADAOTestMemoryHarness(
        params,
        maxEntries = 16,
        reqReadyDelay = 1,
        memRespLatency = 2
      )
    ) { dut =>
      val swym = DADAODecoderTable.entries(DADAODecoderTable.swymId)
      holdResetAt(dut, testPc)
      loadEntry(
        dut,
        0,
        testPc,
        swym.value,
        fault = true,
        faultCode = DADAOFaultCode.Unmapped
      )
      releasePcInit(dut)

      var cycles = 0
      while (
        !dut.io.debugFault.peek().litToBoolean &&
        cycles < 16
      ) {
        dut.clock.step()
        cycles += 1
      }

      dut.io.debugFault.expect(true.B)
      dut.io.debugFaultCode.expect(
        DADAOFaultCode.Unmapped.U
      )
      dut.io.debugPc.expect(testPc.U)
    }
  }

  it should "consume a framed load request and emit a framed result" in {
    test(
      new DADAOTestMemoryHarness(
        params,
        maxEntries = 16,
        reqReadyDelay = 1,
        memRespLatency = 1
      )
    ) { dut =>
      val swym = DADAODecoderTable.entries(DADAODecoderTable.swymId)
      val loadWire = DADAOTestUartFrame.encode(
        "load",
        sequence = 1,
        address = testPc,
        payload = encodeUInt(swym.value, 4)
      )
      val loadFrame = DADAOTestUartFrame.decode(loadWire)
      assert(loadFrame.frameType == "load")
      assert(loadFrame.address == testPc)

      holdResetAt(dut, testPc)
      loadEntry(
        dut,
        0,
        loadFrame.address,
        decodeUInt(loadFrame.payload)
      )
      releasePcInit(dut)

      var cycles = 0
      while (
        dut.io.debugPc.peek().litValue != testPc + 4 &&
        cycles < 32
      ) {
        dut.clock.step()
        cycles += 1
      }

      val retiredPc = dut.io.debugPc.peek().litValue
      dut.io.debugPc.expect((testPc + 4).U)

      val resultWire = DADAOTestUartFrame.encode(
        "result",
        sequence = 2,
        address = testPc,
        payload = encodeUInt(retiredPc, 8)
      )
      val resultFrame = DADAOTestUartFrame.decode(resultWire)
      assert(resultFrame.frameType == "result")
      assert(resultFrame.sequence == 2)
      assert(resultFrame.address == testPc)
      assert(decodeUInt(resultFrame.payload) == retiredPc)
    }
  }

  it should "commit ALU register writes with PC in the same Core cycle" in {
    test(
      new DADAOTestMemoryHarness(
        params,
        maxEntries = 16,
        reqReadyDelay = 1,
        memRespLatency = 1
      )
    ) { dut =>
      val id = "add.ut_orrr_rd"
      val execEntry = DADAOExecTable.entries(
        DADAOExecTable.ids.indexOf(id)
      )
      val baseWord = DADAODecoderTable.entries(execEntry.id).value
      val word =
        setField(
          setField(
            setField(baseWord, 12, 1),
            6,
            2
          ),
          0,
          3
        )

      holdResetAt(dut, testPc)
      loadRegister(
        dut,
        DADAORegBank.Rd,
        2,
        BigInt("ffffffff", 16)
      )
      loadRegister(dut, DADAORegBank.Rd, 3, 1)
      loadEntry(dut, 0, testPc, word)
      releasePcInit(dut)

      var cycles = 0
      while (
        dut.io.debugPc.peek().litValue != testPc + 4 &&
        cycles < 32
      ) {
        dut.clock.step()
        cycles += 1
      }

      dut.io.debugPc.expect((testPc + 4).U)
      dut.io.debugRegBank.poke(DADAORegBank.Rd.U)
      dut.io.debugRegAddr.poke(1.U)
      dut.io.debugRegData.expect(0.U)
    }
  }

  it should "execute a single load through the DATA memory owner" in {
    test(
      new DADAOTestMemoryHarness(
        params,
        maxEntries = 16,
        reqReadyDelay = 1,
        memRespLatency = 2
      )
    ) { dut =>
      val loadId = "ld.uw_rrii_rd"
      val loadEntryIndex = DADAODecoderTable.ids.indexOf(loadId)
      val baseWord = DADAODecoderTable.entries(loadEntryIndex).value
      val word = setField(setField(baseWord, 18, 1), 12, 2)
      val dataAddress = testPc + 0x100

      holdResetAt(dut, testPc)
      loadRegister(dut, DADAORegBank.Rb, 2, dataAddress)
      loadEntry(dut, 0, testPc, word)
      loadEntry(
        dut,
        1,
        dataAddress,
        BigInt("beef000000000000", 16),
        instruction = false
      )
      releasePcInit(dut)

      var cycles = 0
      var observedLoadWrite = false
      var observedLoadWriteData = BigInt(0)
      var observedResponseData = BigInt(0)
      while (
        dut.io.debugPc.peek().litValue != testPc + 4 &&
        cycles < 64
      ) {
        dut.clock.step()
        if (dut.io.debugLoadWrite.peek().litToBoolean) {
          observedLoadWrite = true
          observedLoadWriteData = dut.io.debugLoadWriteData.peek().litValue
          observedResponseData =
            dut.io.debugDataResponseData.peek().litValue
        }
        cycles += 1
      }

      dut.io.debugPc.expect((testPc + 4).U)
      dut.io.debugFault.expect(false.B)
      dut.io.debugDataRequestAddr.expect(dataAddress.U)
      assert(observedLoadWrite, "load did not assert its register write")
      assert(
        observedResponseData == BigInt("beef", 16),
        s"unexpected load response $observedResponseData"
      )
      assert(observedLoadWriteData == BigInt("beef", 16))
      dut.io.debugRegBank.poke(DADAORegBank.Rb.U)
      dut.io.debugRegAddr.poke(2.U)
      dut.clock.step()
      dut.io.debugRegData.expect(dataAddress.U)
      dut.io.debugRegBank.poke(DADAORegBank.Rd.U)
      dut.io.debugRegAddr.poke(1.U)
      dut.clock.step()
      dut.io.debugRegData.expect(BigInt("beef", 16).U)
      assert(dut.io.stats.requestCount.peek().litValue >= 2)
    }
  }

  it should "keep the load PC and destination unchanged on data fault" in {
    test(
      new DADAOTestMemoryHarness(
        params,
        maxEntries = 16,
        reqReadyDelay = 1,
        memRespLatency = 1
      )
    ) { dut =>
      val loadId = "ld.ub_rrii_rd"
      val loadEntryIndex = DADAODecoderTable.ids.indexOf(loadId)
      val baseWord = DADAODecoderTable.entries(loadEntryIndex).value
      val word = setField(setField(baseWord, 18, 1), 12, 2)
      val dataAddress = testPc + 0x100

      holdResetAt(dut, testPc)
      loadRegister(dut, DADAORegBank.Rb, 2, dataAddress)
      loadEntry(dut, 0, testPc, word)
      loadEntry(
        dut,
        1,
        dataAddress,
        0,
        fault = true,
        faultCode = DADAOFaultCode.Unmapped,
        instruction = false
      )
      releasePcInit(dut)

      var cycles = 0
      while (
        !dut.io.debugFault.peek().litToBoolean &&
        cycles < 64
      ) {
        dut.clock.step()
        cycles += 1
      }

      dut.io.debugFault.expect(true.B)
      dut.io.debugFaultCode.expect(DADAOFaultCode.Unmapped.U)
      dut.io.debugPc.expect(testPc.U)
      dut.io.debugRegBank.poke(DADAORegBank.Rd.U)
      dut.io.debugRegAddr.poke(1.U)
      dut.clock.step()
      dut.io.debugRegData.expect(0.U)
    }
  }

  it should "execute RD, RB, and RA source stores and read values back" in {
    val cases = Seq(
      (
        "st.w_rrii_rd",
        DADAORegBank.Rd,
        1,
        BigInt("beef", 16),
        "ld.uw_rrii_rd",
        BigInt("beef", 16),
        0x03
      ),
      (
        "st.o_rrii_rb",
        DADAORegBank.Rb,
        0,
        BigInt(0),
        "ld.o_rrii_rd",
        testPc,
        0xff
      ),
      (
        "st.o_rrii_ra",
        DADAORegBank.Ra,
        1,
        BigInt("0123456789abcdef", 16),
        "ld.o_rrii_rd",
        BigInt("0123456789abcdef", 16),
        0xff
      )
    )

    cases.foreach {
      case (
            storeId,
            sourceBank,
            sourceReg,
            registerValue,
            loadId,
            expectedValue,
            expectedWstrb
          ) =>
        checkStoreRoundTrip(
          storeId,
          sourceBank,
          sourceReg,
          registerValue,
          loadId,
          expectedValue,
          expectedWstrb
        )
    }
  }

  it should "keep the store PC unchanged and write nothing on fault" in {
    test(
      new DADAOTestMemoryHarness(
        params,
        maxEntries = 16,
        reqReadyDelay = 1,
        memRespLatency = 1
      )
    ) { dut =>
      val storeId = "st.o_rrii_rd"
      val storeEntryIndex = DADAODecoderTable.ids.indexOf(storeId)
      val storeBaseWord = DADAODecoderTable.entries(storeEntryIndex).value
      val storeWord = setField(setField(storeBaseWord, 18, 1), 12, 2)
      val dataAddress = testPc + 0x100

      holdResetAt(dut, testPc)
      loadRegister(dut, DADAORegBank.Rd, 1, BigInt("deadbeef", 16))
      loadRegister(dut, DADAORegBank.Rb, 2, dataAddress)
      loadEntry(dut, 0, testPc, storeWord)
      loadEntry(
        dut,
        1,
        dataAddress,
        0,
        fault = true,
        faultCode = DADAOFaultCode.Unmapped,
        instruction = false
      )
      releasePcInit(dut)

      var cycles = 0
      while (
        !dut.io.debugFault.peek().litToBoolean &&
        cycles < 64
      ) {
        dut.clock.step()
        cycles += 1
      }

      dut.io.debugFault.expect(true.B)
      dut.io.debugFaultCode.expect(DADAOFaultCode.Unmapped.U)
      dut.io.debugPc.expect(testPc.U)
      dut.io.stats.writeCount.expect(0.U)
    }
  }

  it should "precheck data faults before issuing a memory request" in {
    val cases = Seq(
      (
        "ld.o_rrii_rd",
        DADAORegBank.Rd,
        1,
        BigInt(0),
        legacyExitBase + 1,
        DADAOFaultCode.Unmapped,
        false
      ),
      (
        "st.w_rrii_rd",
        DADAORegBank.Rd,
        1,
        BigInt("deadbeef", 16),
        testPc + 0x101,
        DADAOFaultCode.Malign,
        true
      ),
      (
        "st.o_rrii_rd",
        DADAORegBank.Rd,
        1,
        BigInt("deadbeef", 16),
        params.bootRomBase,
        DADAOFaultCode.Illi,
        true
      )
    )

    cases.foreach {
      case (
            instructionId,
            sourceBank,
            sourceReg,
            sourceValue,
            dataAddress,
            expectedFaultCode,
            isStore
          ) =>
        checkDataAccessFaultBeforeRequest(
          instructionId,
          sourceBank,
          sourceReg,
          sourceValue,
          dataAddress,
          expectedFaultCode,
          isStore
        )
    }
  }

  it should "precheck an unmapped fetch before issuing a request" in {
    test(
      new DADAOTestMemoryHarness(
        params,
        maxEntries = 16,
        reqReadyDelay = 1,
        memRespLatency = 1
      )
    ) { dut =>
      val unmappedPc = legacyExitBase + 4

      holdResetAt(dut, unmappedPc)
      releasePcInit(dut)

      dut.io.debugFault.expect(true.B)
      dut.io.debugFaultCode.expect(DADAOFaultCode.Unmapped.U)
      dut.io.debugFaultReason.expect(
        DADAODebugFaultReason.AccessFault.U
      )
      dut.io.debugPc.expect(unmappedPc.U)
      dut.io.stats.requestCount.expect(0.U)
    }
  }

  it should "load three narrow values through ldm" in {
    test(
      new DADAOTestMemoryHarness(
        params,
        maxEntries = 16,
        reqReadyDelay = 1,
        memRespLatency = 2
      )
    ) { dut =>
      val dataAddress = testPc + 0x100
      val word = codedBlockInstruction(
        "ldm.uw_rrri_rd",
        startReg = 3,
        baseReg = 2,
        offsetReg = 1,
        count = 3
      )

      holdResetAt(dut, testPc)
      loadRegister(dut, DADAORegBank.Rb, 2, dataAddress)
      loadRegister(dut, DADAORegBank.Rd, 1, 0)
      loadEntry(dut, 0, testPc, word)
      loadEntry(
        dut,
        1,
        dataAddress,
        BigInt("1122334455660000", 16),
        instruction = false
      )
      releasePcInit(dut)

      var cycles = 0
      while (
        dut.io.debugPc.peek().litValue != testPc + 4 &&
        cycles < 256
      ) {
        dut.clock.step()
        cycles += 1
      }

      dut.io.debugPc.expect((testPc + 4).U)
      dut.io.debugFault.expect(false.B)
      for ((reg, expected) <- Seq(
            3 -> BigInt("1122", 16),
            4 -> BigInt("3344", 16),
            5 -> BigInt("5566", 16)
           )) {
        dut.io.debugRegBank.poke(DADAORegBank.Rd.U)
        dut.io.debugRegAddr.poke(reg.U)
        dut.clock.step()
        dut.io.debugRegData.expect(expected.U)
      }
      dut.io.stats.writeCount.expect(0.U)
      assert(dut.io.stats.requestCount.peek().litValue >= 4)
    }
  }

  it should "store three narrow values and load them back" in {
    test(
      new DADAOTestMemoryHarness(
        params,
        maxEntries = 16,
        reqReadyDelay = 1,
        memRespLatency = 2
      )
    ) { dut =>
      val dataAddress = testPc + 0x100
      val storeWord = codedBlockInstruction(
        "stm.w_rrri_rd",
        startReg = 3,
        baseReg = 2,
        offsetReg = 1,
        count = 3
      )
      val loadWord = codedBlockInstruction(
        "ldm.uw_rrri_rd",
        startReg = 6,
        baseReg = 2,
        offsetReg = 1,
        count = 3
      )

      holdResetAt(dut, testPc)
      loadRegister(dut, DADAORegBank.Rb, 2, dataAddress)
      loadRegister(dut, DADAORegBank.Rd, 1, 0)
      loadRegister(dut, DADAORegBank.Rd, 3, BigInt("1122", 16))
      loadRegister(dut, DADAORegBank.Rd, 4, BigInt("3344", 16))
      loadRegister(dut, DADAORegBank.Rd, 5, BigInt("5566", 16))
      loadInstructionBeat(
        dut,
        0,
        testPc,
        storeWord,
        loadWord
      )
      loadEntry(
        dut,
        1,
        dataAddress,
        0,
        instruction = false
      )
      releasePcInit(dut)

      var cycles = 0
      while (
        dut.io.debugPc.peek().litValue != testPc + 8 &&
        cycles < 512
      ) {
        dut.clock.step()
        cycles += 1
      }

      dut.io.debugPc.expect((testPc + 8).U)
      dut.io.debugFault.expect(false.B)
      for ((reg, expected) <- Seq(
            6 -> BigInt("1122", 16),
            7 -> BigInt("3344", 16),
            8 -> BigInt("5566", 16)
           )) {
        dut.io.debugRegBank.poke(DADAORegBank.Rd.U)
        dut.io.debugRegAddr.poke(reg.U)
        dut.clock.step()
        dut.io.debugRegData.expect(expected.U)
      }
      dut.io.stats.writeCount.expect(3.U)
      assert(dut.io.stats.requestCount.peek().litValue >= 8)
    }
  }

  it should "discard buffered ldm results when a later response faults" in {
    test(
      new DADAOTestMemoryHarness(
        params,
        maxEntries = 16,
        reqReadyDelay = 1,
        memRespLatency = 1
      )
    ) { dut =>
      val dataAddress = testPc + 0x100
      val word = codedBlockInstruction(
        "ldm.o_rrri_rd",
        startReg = 3,
        baseReg = 2,
        offsetReg = 1,
        count = 2
      )

      holdResetAt(dut, testPc)
      loadRegister(dut, DADAORegBank.Rb, 2, dataAddress)
      loadRegister(dut, DADAORegBank.Rd, 1, 0)
      loadRegister(dut, DADAORegBank.Rd, 3, BigInt("1234", 16))
      loadRegister(dut, DADAORegBank.Rd, 4, BigInt("5678", 16))
      loadEntry(dut, 0, testPc, word)
      loadEntry(
        dut,
        1,
        dataAddress,
        BigInt("1111111111111111", 16),
        instruction = false
      )
      loadEntry(
        dut,
        2,
        dataAddress + 8,
        0,
        fault = true,
        faultCode = DADAOFaultCode.Unmapped,
        instruction = false
      )
      releasePcInit(dut)

      var cycles = 0
      while (
        !dut.io.debugFault.peek().litToBoolean &&
        cycles < 128
      ) {
        dut.clock.step()
        cycles += 1
      }

      dut.io.debugFault.expect(true.B)
      dut.io.debugFaultCode.expect(DADAOFaultCode.Unmapped.U)
      dut.io.debugPc.expect(testPc.U)
      dut.io.debugRegBank.poke(DADAORegBank.Rd.U)
      dut.io.debugRegAddr.poke(3.U)
      dut.clock.step()
      dut.io.debugRegData.expect(BigInt("1234", 16).U)
      dut.io.debugRegAddr.poke(4.U)
      dut.clock.step()
      dut.io.debugRegData.expect(BigInt("5678", 16).U)
    }
  }

  it should "reject stm before any store when a later address is unmapped" in {
    test(
      new DADAOTestMemoryHarness(
        params,
        maxEntries = 16,
        reqReadyDelay = 1,
        memRespLatency = 1
      )
    ) { dut =>
      val dataAddress = params.ramBase + params.ramSize - 8
      val word = codedBlockInstruction(
        "stm.o_rrri_rd",
        startReg = 3,
        baseReg = 2,
        offsetReg = 1,
        count = 2
      )

      holdResetAt(dut, testPc)
      loadRegister(dut, DADAORegBank.Rb, 2, dataAddress)
      loadRegister(dut, DADAORegBank.Rd, 1, 0)
      loadRegister(dut, DADAORegBank.Rd, 3, BigInt("1111", 16))
      loadRegister(dut, DADAORegBank.Rd, 4, BigInt("2222", 16))
      loadEntry(dut, 0, testPc, word)
      releasePcInit(dut)

      var cycles = 0
      while (
        !dut.io.debugFault.peek().litToBoolean &&
        cycles < 128
      ) {
        dut.clock.step()
        cycles += 1
      }

      dut.io.debugFault.expect(true.B)
      dut.io.debugFaultCode.expect(DADAOFaultCode.Unmapped.U)
      dut.io.debugPc.expect(testPc.U)
      dut.io.stats.requestCount.expect(1.U)
      dut.io.stats.writeCount.expect(0.U)
    }
  }

  it should "snapshot the ldm offset when the destination range includes it" in {
    test(
      new DADAOTestMemoryHarness(
        params,
        maxEntries = 16,
        reqReadyDelay = 1,
        memRespLatency = 1
      )
    ) { dut =>
      val base = testPc + 0x100
      val offset = BigInt("10", 16)
      val dataAddress = base + offset
      val word = codedBlockInstruction(
        "ldm.uw_rrri_rd",
        startReg = 1,
        baseReg = 2,
        offsetReg = 1,
        count = 2
      )

      holdResetAt(dut, testPc)
      loadRegister(dut, DADAORegBank.Rb, 2, base)
      loadRegister(dut, DADAORegBank.Rd, 1, offset)
      loadEntry(dut, 0, testPc, word)
      loadEntry(
        dut,
        1,
        dataAddress,
        BigInt("aaaabbbb00000000", 16),
        instruction = false
      )
      releasePcInit(dut)

      var cycles = 0
      while (
        dut.io.debugPc.peek().litValue != testPc + 4 &&
        cycles < 256
      ) {
        dut.clock.step()
        cycles += 1
      }

      dut.io.debugPc.expect((testPc + 4).U)
      dut.io.debugFault.expect(false.B)
      dut.io.debugRegBank.poke(DADAORegBank.Rd.U)
      dut.io.debugRegAddr.poke(1.U)
      dut.clock.step()
      dut.io.debugRegData.expect(BigInt("aaaa", 16).U)
      dut.io.debugRegAddr.poke(2.U)
      dut.clock.step()
      dut.io.debugRegData.expect(BigInt("bbbb", 16).U)
      assert(dut.io.stats.requestCount.peek().litValue >= 3)
    }
  }

  it should "D5 execute trap and escape through the Core control path" in {
    test(
      new DADAOTestMemoryHarness(
        params,
        maxEntries = 16,
        reqReadyDelay = 1,
        memRespLatency = 1
      )
    ) { dut =>
      val hmonVector = testPc + 0x300
      val swym = DADAODecoderTable.entries(DADAODecoderTable.swymId).value
      val trapWord = cfxImmediateWord(
        "trap_ciii_cfx",
        DADAOCfxCode.Hmon,
        BigInt("55", 16)
      )
      val escapeWord = cfxImmediateWord(
        "escape_ciii_cfx",
        DADAOCfxCode.Hmon,
        1
      )

      holdResetAt(dut, testPc)
      writeCfx(
        dut,
        DADAOCfxCode.Hmon,
        3,
        10,
        hmonVector
      )
      loadInstructionBeat(dut, 0, testPc, trapWord, swym)
      loadInstructionBeat(dut, 1, hmonVector, swym, escapeWord)
      releasePcInit(dut)

      waitForPc(dut, testPc + 8)
      dut.io.debugFault.expect(false.B)
      dut.io.debugCfxStatus.runMode.expect(DADAORunMode.Hypv.U)
      dut.io.debugCfxStatus.cfxCode.expect(DADAOCfxCode.Hmon.U)
      readCfx(dut, DADAOCfxCode.Hmon, 5, 2) should be(
        DADAOCfxCause.Trap
      )
      readCfx(dut, DADAOCfxCode.Hmon, 5, 3) should be(testPc)
      readCfx(dut, DADAOCfxCode.Hmon, 4, 2) should be(1)
      readCfx(dut, DADAOCfxCode.Hmon, 4, 5) should be(1)
    }
  }

  it should "D5 write an RD through cfx2rd in the Core" in {
    test(
      new DADAOTestMemoryHarness(
        params,
        maxEntries = 16,
        reqReadyDelay = 1,
        memRespLatency = 1
      )
    ) { dut =>
      val value = BigInt("123456789abcdef0", 16)
      val word = cfx2Word(
        "cfx2rd_crrr_cfx",
        DADAOCfxCode.Power,
        6,
        1,
        5
      )

      holdResetAt(dut, testPc)
      writeCfx(
        dut,
        DADAOCfxCode.Power,
        6,
        1,
        value
      )
      loadEntry(dut, 0, testPc, word)
      releasePcInit(dut)

      waitForPc(dut, testPc + 4)
      dut.io.debugFault.expect(false.B)
      expectRegister(dut, DADAORegBank.Rd, 5, value)
    }
  }

  it should "D5 redirect CFXPERM without writing the destination RD" in {
    test(
      new DADAOTestMemoryHarness(
        params,
        maxEntries = 16,
        reqReadyDelay = 1,
        memRespLatency = 1
      )
    ) { dut =>
      val hmonVector = testPc + 0x320
      val sentinel = BigInt("deadbeef", 16)
      val word = cfx2Word(
        "cfx2rd_crrr_cfx",
        DADAOCfxCode.Hmon,
        4,
        0,
        5
      )

      holdResetAt(dut, testPc)
      writeCfx(
        dut,
        DADAOCfxCode.Hmon,
        3,
        10,
        hmonVector
      )
      writeCfx(
        dut,
        DADAOCfxCode.Hmon,
        3,
        2,
        BigInt("fffffffffffffff7", 16)
      )
      loadRegister(dut, DADAORegBank.Rd, 5, sentinel)
      loadEntry(dut, 0, testPc, word)
      releasePcInit(dut)

      waitForPc(dut, hmonVector)
      dut.io.debugFault.expect(false.B)
      dut.io.debugCfxStatus.cfxCode.expect(DADAOCfxCode.Hmon.U)
      readCfx(dut, DADAOCfxCode.Hmon, 5, 2) should be(
        DADAOCfxCause.Perm
      )
      readCfx(dut, DADAOCfxCode.Hmon, 5, 3) should be(testPc)
      readCfx(dut, DADAOCfxCode.Hmon, 5, 4) should be(word)
      readCfx(dut, DADAOCfxCode.Hmon, 4, 2) should be(0)
      readCfx(dut, DADAOCfxCode.Hmon, 4, 3) should be(1)
      expectRegister(dut, DADAORegBank.Rd, 5, sentinel)
    }
  }

  it should "D5 redirect CFXREG for a read-only CFX write" in {
    test(
      new DADAOTestMemoryHarness(
        params,
        maxEntries = 16,
        reqReadyDelay = 1,
        memRespLatency = 1
      )
    ) { dut =>
      val hmonVector = testPc + 0x340
      val sentinel = BigInt("feedface", 16)
      val word = cfx2Word(
        "cfx2rc_crrr_cfx",
        DADAOCfxCode.Power,
        4,
        0,
        7
      )

      holdResetAt(dut, testPc)
      writeCfx(
        dut,
        DADAOCfxCode.Hmon,
        3,
        10,
        hmonVector
      )
      loadRegister(dut, DADAORegBank.Rd, 7, sentinel)
      loadEntry(dut, 0, testPc, word)
      releasePcInit(dut)

      waitForPc(dut, hmonVector)
      dut.io.debugFault.expect(false.B)
      dut.io.debugCfxStatus.cfxCode.expect(DADAOCfxCode.Hmon.U)
      readCfx(dut, DADAOCfxCode.Hmon, 5, 2) should be(
        DADAOCfxCause.Reg
      )
      readCfx(dut, DADAOCfxCode.Hmon, 5, 3) should be(testPc)
      readCfx(dut, DADAOCfxCode.Hmon, 4, 2) should be(0)
      readCfx(dut, DADAOCfxCode.Hmon, 4, 3) should be(1)
      expectRegister(dut, DADAORegBank.Rd, 7, sentinel)
    }
  }

  it should "D5 raise CFXESC for escape with no valid frame" in {
    test(
      new DADAOTestMemoryHarness(
        params,
        maxEntries = 16,
        reqReadyDelay = 1,
        memRespLatency = 1
      )
    ) { dut =>
      val powerVector = testPc + 0x360
      val word = cfxImmediateWord(
        "escape_ciii_cfx",
        DADAOCfxCode.Hmon,
        0
      )

      holdResetAt(dut, testPc)
      writeCfx(
        dut,
        DADAOCfxCode.Power,
        3,
        10,
        powerVector
      )
      loadEntry(dut, 0, testPc, word)
      releasePcInit(dut)

      waitForPc(dut, powerVector)
      dut.io.debugFault.expect(false.B)
      dut.io.debugCfxStatus.runMode.expect(DADAORunMode.Hypv.U)
      dut.io.debugCfxStatus.cfxCode.expect(DADAOCfxCode.Power.U)
      readCfx(dut, DADAOCfxCode.Power, 5, 2) should be(
        DADAOCfxCause.Esc
      )
      readCfx(dut, DADAOCfxCode.Power, 5, 3) should be(testPc)
      readCfx(dut, DADAOCfxCode.Power, 4, 2) should be(0)
      readCfx(dut, DADAOCfxCode.Power, 4, 3) should be(1)
    }
  }
}
