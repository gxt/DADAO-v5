package dadao

import chisel3._
import chiseltest._
import org.scalatest.flatspec.AnyFlatSpec

final class DADAOMemoryOracleProbeIO(val params: DADAOParams) extends Bundle {
  val word = Input(UInt(32.W))
  val baseValue = Input(UInt(64.W))
  val offsetValue = Input(UInt(64.W))
  val address = Input(UInt(params.addrBits.W))
  val sourceValue = Input(UInt(64.W))
  val memoryBeat = Input(UInt(64.W))

  val decoderFault = Output(Bool())
  val decoderFaultCode = Output(UInt(8.W))
  val isLoad = Output(Bool())
  val isStore = Output(Bool())
  val isBlock = Output(Bool())
  val requestAddr = Output(UInt(params.addrBits.W))
  val requestSize = Output(UInt(3.W))
  val requestWdata = Output(UInt(64.W))
  val requestWstrb = Output(UInt(8.W))
  val loadDestValid = Output(Bool())
  val loadDestBank = Output(UInt(2.W))
  val loadDestAddr = Output(UInt(6.W))
  val loadDestData = Output(UInt(64.W))
  val blockLoadValue = Output(UInt(64.W))
  val blockFirstAddress = Output(UInt(params.addrBits.W))
  val blockCount = Output(UInt(6.W))
  val blockStartReg = Output(UInt(6.W))
  val blockBaseReg = Output(UInt(6.W))
  val blockOffsetReg = Output(UInt(6.W))
  val blockTargetBank = Output(UInt(2.W))
  val accessFault = Output(Bool())
  val accessFaultCode = Output(UInt(8.W))
  val mergedBeat = Output(UInt(64.W))
  val extractedBeat = Output(UInt(64.W))
}

final class DADAOMemoryOracleProbe(
    val params: DADAOParams = DADAOParams()
) extends Module {
  val io = IO(new DADAOMemoryOracleProbeIO(params))

  private val decoder = Module(new DADAODecoder)
  decoder.io.word := io.word

  private val loadExec = Module(new DADAOLoadExec(params))
  loadExec.io.decoded := decoder.io.decoded
  loadExec.io.baseValue := io.baseValue
  loadExec.io.responseData := DADAOByteLane.readValue(
    io.memoryBeat,
    io.requestAddr(2, 0),
    io.requestSize
  )
  loadExec.io.responseValid := true.B
  loadExec.io.responseFault := false.B

  private val storeExec = Module(new DADAOStoreExec(params))
  storeExec.io.decoded := decoder.io.decoded
  storeExec.io.baseValue := io.baseValue
  storeExec.io.sourceValue := io.sourceValue

  private val blockExec = Module(new DADAOBlockMemExec(params))
  blockExec.io.decoded := decoder.io.decoded
  blockExec.io.baseValue := io.baseValue
  blockExec.io.offsetValue := io.offsetValue
  blockExec.io.address := io.address
  blockExec.io.sourceValue := io.sourceValue
  blockExec.io.responseValue := DADAOByteLane.readValue(
    io.memoryBeat,
    io.address(2, 0),
    blockExec.io.requestSize
  )

  io.decoderFault := decoder.io.control.fault
  io.decoderFaultCode := decoder.io.control.faultCode
  io.isBlock := blockExec.io.isBlock
  io.isLoad :=
    Mux(blockExec.io.isBlock, blockExec.io.isLoad, loadExec.io.isLoad)
  io.isStore :=
    Mux(blockExec.io.isBlock, blockExec.io.isStore, storeExec.io.isStore)
  io.requestAddr := Mux(
    blockExec.io.isBlock,
    io.address,
    Mux(
      storeExec.io.isStore,
      storeExec.io.requestAddr,
      loadExec.io.requestAddr
    )
  )
  io.requestSize := Mux(
    blockExec.io.isBlock,
    blockExec.io.requestSize,
    Mux(
      storeExec.io.isStore,
      storeExec.io.requestSize,
      loadExec.io.requestSize
    )
  )
  io.requestWdata := Mux(
    blockExec.io.isBlock,
    blockExec.io.requestWdata,
    storeExec.io.requestWdata
  )
  io.requestWstrb := Mux(
    blockExec.io.isBlock,
    blockExec.io.requestWstrb,
    storeExec.io.requestWstrb
  )
  io.loadDestValid := loadExec.io.write.valid
  io.loadDestBank := loadExec.io.write.bank
  io.loadDestAddr := loadExec.io.write.addr
  io.loadDestData := loadExec.io.write.data
  io.blockLoadValue := blockExec.io.loadValue
  io.blockFirstAddress := blockExec.io.firstAddress
  io.blockCount := blockExec.io.count
  io.blockStartReg := blockExec.io.startRegAddr
  io.blockBaseReg := blockExec.io.baseRegAddr
  io.blockOffsetReg := blockExec.io.offsetRegAddr
  io.blockTargetBank := blockExec.io.targetBank

  private val accessCheck = Module(new DADAOAccessCheck(params))
  accessCheck.io.addr := io.requestAddr
  accessCheck.io.write :=
    Mux(blockExec.io.isBlock, blockExec.io.isStore, storeExec.io.isStore)
  accessCheck.io.size := io.requestSize
  accessCheck.io.kind := DADAOMemKind.Data.U
  io.accessFault := accessCheck.io.fault
  io.accessFaultCode := accessCheck.io.faultCode
  io.mergedBeat := DADAOByteLane.mergeWrite(
    io.memoryBeat,
    io.requestWdata,
    io.requestAddr(2, 0),
    io.requestSize,
    io.requestWstrb
  )
  io.extractedBeat := DADAOByteLane.readValue(
    io.memoryBeat,
    io.requestAddr(2, 0),
    io.requestSize
  )
}

final class DADAOMemoryOracleSpec
    extends AnyFlatSpec
    with ChiselScalatestTester {
  behavior of "DADAO memory oracle"

  private val params = DADAOParams()
  private val testPc = BigInt("fc0000000000", 16)

  private def loadEntry(
      dut: DADAOTestMemoryHarness,
      index: Int,
      address: BigInt,
      data: BigInt,
      writable: Boolean = true,
      fault: Boolean = false,
      faultCode: Int = 0
  ): Unit = {
    dut.io.load.valid.poke(true.B)
    dut.io.load.index.poke(index.U)
    dut.io.load.address.poke(address.U)
    dut.io.load.data.poke(data.U)
    dut.io.load.writable.poke(writable.B)
    dut.io.load.fault.poke(fault.B)
    dut.io.load.faultCode.poke(faultCode.U)
    dut.clock.step()
    dut.io.load.valid.poke(false.B)
  }

  private def resetHarness(dut: DADAOTestMemoryHarness): Unit = {
    dut.io.testRegWrite.valid.poke(false.B)
    dut.io.testRegWrite.bank.poke(DADAORegBank.Rd.U)
    dut.io.testRegWrite.addr.poke(0.U)
    dut.io.testRegWrite.data.poke(0.U)
    dut.io.debugRegBank.poke(DADAORegBank.Rd.U)
    dut.io.debugRegAddr.poke(0.U)
    dut.io.debugMemIndex.poke(0.U)
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
    dut.io.pcInit.poke(testPc.U)
    dut.reset.poke(true.B)
    dut.clock.step(2)
    dut.reset.poke(false.B)
    dut.clock.step()
  }

  private def loadRegister(
      dut: DADAOTestMemoryHarness,
      register: DADAOMemoryRegValue
  ): Unit = {
    dut.io.testRegWrite.valid.poke(true.B)
    dut.io.testRegWrite.bank.poke(register.bank.U)
    dut.io.testRegWrite.addr.poke(register.index.U)
    dut.io.testRegWrite.data.poke(register.value.U)
    dut.clock.step()
    dut.io.testRegWrite.valid.poke(false.B)
  }

  private def loadMemory(
      dut: DADAOTestMemoryHarness,
      memory: DADAOMemoryValue
  ): Unit = {
    loadEntry(
      dut,
      memory.index,
      memory.address,
      memory.data,
      writable = memory.writable,
      fault = memory.fault,
      faultCode = memory.faultCode
    )
  }

  private def runVector(
      dut: DADAOTestMemoryHarness,
      vector: DADAOMemoryOracleVector
  ): Unit = {
    resetHarness(dut)

    vector.initialRegisters.foreach(loadRegister(dut, _))
    vector.initialMemory.foreach(loadMemory(dut, _))
    loadEntry(
      dut,
      0,
      testPc,
      vector.word << 32
    )

    dut.io.pcInitValid.poke(false.B)
    dut.clock.step()

    var cycles = 0
    var done = false
    while (!done && cycles < 512) {
      val fault = dut.io.debugFault.peek().litToBoolean
      val pc = dut.io.debugPc.peek().litValue
      done =
        if (vector.expectedFault) fault
        else fault || pc == vector.expectedPc
      if (!done) {
        dut.clock.step()
        cycles += 1
      }
    }

    val observedPc = dut.io.debugPc.peek().litValue
    val observedFault = dut.io.debugFault.peek().litToBoolean
    val observedFaultCode = dut.io.debugFaultCode.peek().litValue.toInt
    val observedRequests = dut.io.stats.requestCount.peek().litValue.toInt

    withClue(s"${vector.name}: PC mismatch: ") {
      assert(observedPc == vector.expectedPc)
    }
    withClue(s"${vector.name}: fault state mismatch: ") {
      assert(observedFault == vector.expectedFault)
    }
    withClue(s"${vector.name}: fault code mismatch: ") {
      assert(observedFaultCode == vector.expectedFaultCode)
    }
    withClue(s"${vector.name}: data request count mismatch: ") {
      assert(observedRequests == vector.expectedDataRequests + 1)
    }

    vector.expectedRegisters.foreach { register =>
      dut.io.debugRegBank.poke(register.bank.U)
      dut.io.debugRegAddr.poke(register.index.U)
      withClue(
        s"${vector.name}: bank=${register.bank} reg=${register.index}: "
      ) {
        dut.io.debugRegData.expect(register.value.U)
      }
    }

    vector.expectedMemory.foreach { memory =>
      dut.io.debugMemIndex.poke(memory.index.U)
      withClue(s"${vector.name}: memory index=${memory.index} valid: ") {
        dut.io.debugMemValid.expect(true.B)
      }
      dut.io.debugMemAddress.expect(memory.address.U)
      dut.io.debugMemData.expect(memory.data.U)
      dut.io.debugMemWritable.expect(memory.writable.B)
      dut.io.debugMemFault.expect(memory.fault.B)
      dut.io.debugMemFaultCode.expect(memory.faultCode.U)
    }
  }

  private def initialRegister(
      vector: DADAOMemoryOracleVector,
      bank: Int,
      index: Int
  ): BigInt =
    vector.initialRegisters
      .find(register => register.bank == bank && register.index == index)
      .map(_.value)
      .getOrElse(0)

  private def initialMemory(
      vector: DADAOMemoryOracleVector,
      address: BigInt
  ): DADAOMemoryValue =
    vector.initialMemory
      .find(_.address == (address & ~BigInt(7)))
      .getOrElse(
        fail(s"${vector.name}: no initial memory beat for 0x${address.toString(16)}")
      )

  private def instructionName(vector: DADAOMemoryOracleVector): String =
    DADAODecoderTable.ids(vector.instructionId)

  private def memoryBank(vector: DADAOMemoryOracleVector): Int = {
    val id = instructionName(vector)
    if (id.endsWith("_rb")) DADAORegBank.Rb
    else if (id.endsWith("_ra")) DADAORegBank.Ra
    else DADAORegBank.Rd
  }

  private def sizeCode(widthBytes: Int): Int =
    widthBytes match {
      case 1 => DADAOMemSize.Byte
      case 2 => DADAOMemSize.Wyde
      case 4 => DADAOMemSize.Tetra
      case 8 => DADAOMemSize.Octa
      case other => fail(s"unsupported memory width: $other")
    }

  private def expectedWstrb(address: BigInt, widthBytes: Int): Int = {
    val widthMask = (1 << widthBytes) - 1
    (widthMask << (address.toInt & 0x7)) & 0xFF
  }

  private def pokeProbe(
      dut: DADAOMemoryOracleProbe,
      vector: DADAOMemoryOracleVector,
      address: BigInt,
      sourceValue: BigInt,
      memoryBeat: BigInt
  ): Unit = {
    dut.io.word.poke(vector.word.U(32.W))
    dut.io.baseValue.poke(
      initialRegister(vector, DADAORegBank.Rb, 2).U
    )
    dut.io.offsetValue.poke(
      initialRegister(vector, DADAORegBank.Rd, 1).U
    )
    dut.io.address.poke(address.U)
    dut.io.sourceValue.poke(sourceValue.U)
    dut.io.memoryBeat.poke(memoryBeat.U)
  }

  private def runDirectVector(
      dut: DADAOMemoryOracleProbe,
      vector: DADAOMemoryOracleVector
  ): Unit = {
    val baseValue = initialRegister(vector, DADAORegBank.Rb, 2)
    val offsetValue = initialRegister(vector, DADAORegBank.Rd, 1)
    val sourceBank = memoryBank(vector)
    val sourceRegister = ((vector.word >> 18) & 0x3f).toInt
    val size = sizeCode(vector.widthBytes)
    val sourceMask =
      if (vector.widthBytes == 8) (BigInt(1) << 64) - 1
      else (BigInt(1) << (vector.widthBytes * 8)) - 1

    if (vector.category == "fault_static") {
      pokeProbe(dut, vector, baseValue, 0, 0)
      dut.io.decoderFault.expect(true.B)
      dut.io.decoderFaultCode.expect(vector.expectedFaultCode.U)
    } else if (
      vector.expectedFault &&
      vector.category == "fault_block_store"
    ) {
      val firstAddress = baseValue + offsetValue
      pokeProbe(dut, vector, firstAddress, 0, 0)
      dut.io.accessFault.expect(false.B)
      val secondAddress = firstAddress + vector.widthBytes
      pokeProbe(dut, vector, secondAddress, 0, 0)
      dut.io.requestAddr.expect(secondAddress.U)
      dut.io.accessFault.expect(true.B)
      dut.io.accessFaultCode.expect(vector.expectedFaultCode.U)
    } else if (vector.category == "fault_block_response") {
      assert(vector.name == "fault-block-load-late-response")
    } else if (vector.expectedFault) {
      pokeProbe(dut, vector, baseValue, 0, 0)
      dut.io.accessFault.expect(true.B)
      dut.io.accessFaultCode.expect(vector.expectedFaultCode.U)
    } else if (vector.isBlock) {
      val currentBeats =
        scala.collection.mutable.Map.empty[BigInt, BigInt]
      vector.initialMemory.foreach { memory =>
        currentBeats(memory.address) = memory.data
      }
      val firstAddress = baseValue + offsetValue
      val addresses =
        Seq.tabulate(vector.count) { index =>
          firstAddress + index * vector.widthBytes
        }
      addresses.zipWithIndex.foreach { case (address, index) =>
        val memory = initialMemory(
          vector,
          if (vector.isStore) address else address
        )
        val beat = currentBeats(memory.address)
        val source =
          initialRegister(vector, sourceBank, sourceRegister + index)
        pokeProbe(dut, vector, address, source, beat)
        dut.io.isBlock.expect(true.B)
        dut.io.decoderFault.expect(false.B)
        dut.io.blockFirstAddress.expect(firstAddress.U)
        dut.io.blockCount.expect(vector.count.U)
        dut.io.blockStartReg.expect(sourceRegister.U)
        dut.io.blockBaseReg.expect(2.U)
        dut.io.blockOffsetReg.expect(1.U)
        dut.io.blockTargetBank.expect(sourceBank.U)
        dut.io.requestSize.expect(size.U)
        if (vector.isStore) {
          dut.io.isStore.expect(true.B)
          dut.io.requestWdata.expect((source & sourceMask).U)
          dut.io.requestWstrb.expect(
            expectedWstrb(address, vector.widthBytes).U
          )
          dut.io.accessFault.expect(false.B)
          currentBeats(memory.address) =
            dut.io.mergedBeat.peek().litValue
        } else {
          dut.io.isLoad.expect(true.B)
          val destination = vector.expectedRegisters
            .find(_.index == sourceRegister + index)
            .getOrElse(
              fail(
                s"${vector.name}: missing destination register " +
                  s"${sourceRegister + index}"
              )
            )
          dut.io.blockLoadValue.expect(destination.value.U)
        }
      }
      vector.expectedMemory.foreach { memory =>
        assert(
          currentBeats(memory.address) == memory.data,
          s"${vector.name}: memory beat 0x${memory.address.toString(16)}"
        )
      }
    } else if (vector.isStore) {
      val source = initialRegister(vector, sourceBank, sourceRegister)
      val memory = initialMemory(vector, baseValue)
      pokeProbe(dut, vector, baseValue, source, memory.data)
      dut.io.isStore.expect(true.B)
      dut.io.isBlock.expect(false.B)
      dut.io.requestAddr.expect(baseValue.U)
      dut.io.requestSize.expect(size.U)
      dut.io.requestWdata.expect((source & sourceMask).U)
      dut.io.requestWstrb.expect(
        expectedWstrb(baseValue, vector.widthBytes).U
      )
      dut.io.accessFault.expect(false.B)
      dut.io.mergedBeat.expect(vector.expectedMemory.head.data.U)
    } else {
      val destination = vector.expectedRegisters.head
      val memory = initialMemory(vector, baseValue)
      pokeProbe(dut, vector, baseValue, 0, memory.data)
      dut.io.isLoad.expect(true.B)
      dut.io.isBlock.expect(false.B)
      dut.io.requestAddr.expect(baseValue.U)
      dut.io.requestSize.expect(size.U)
      dut.io.loadDestValid.expect(true.B)
      dut.io.loadDestBank.expect(destination.bank.U)
      dut.io.loadDestAddr.expect(destination.index.U)
      dut.io.loadDestData.expect(destination.value.U)
      dut.io.accessFault.expect(false.B)
    }

  }

  it should "cover every M1 memory instruction exactly once" in {
    val expectedIds = DADAODecoderTable.ids.zipWithIndex.collect {
      case (id, index)
          if DADAODecoderTable.entries(index).scope == DADAOScope.M1 &&
            (
              id.startsWith("ld.") ||
                id.startsWith("st.") ||
                id.startsWith("ldm.") ||
                id.startsWith("stm.")
            ) =>
        index
    }
    val positive = DADAOMemoryOracleTable.vectors.filter(_.coverage)

    assert(expectedIds.size == 30)
    assert(positive.size == 30)
    assert(positive.map(_.instructionId).distinct.size == 30)
    assert(positive.map(_.instructionId).toSet == expectedIds.toSet)
    assert(positive.map(_.widthBytes).toSet == Set(1, 2, 4, 8))
    assert(
      positive.exists(vector => vector.signed && vector.widthBytes == 1)
    )
    assert(
      DADAOMemoryOracleTable.vectors.count(_.expectedFault) == 8
    )
  }

  it should "validate every generated vector against execution RTL" in {
    test(new DADAOMemoryOracleProbe(params)) { dut =>
      DADAOMemoryOracleTable.vectors.foreach(runDirectVector(dut, _))
    }
  }

  it should "preserve block atomicity for generated fault vectors" in {
    val faultVectors = DADAOMemoryOracleTable.vectors.filter { vector =>
      vector.name == "fault-block-store-late-unmapped" ||
      vector.name == "fault-block-load-late-response"
    }

    test(
      new DADAOTestMemoryHarness(
        params,
        maxEntries = 16,
        reqReadyDelay = 1,
        memRespLatency = 2
      )
    ) { dut =>
      faultVectors.foreach(runVector(dut, _))
    }
  }
}
