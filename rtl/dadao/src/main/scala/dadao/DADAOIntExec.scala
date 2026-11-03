package dadao

import chisel3._
import chisel3.util.{Cat, Fill, Mux1H, MuxLookup}

final class DADAOTestRegWrite extends Bundle {
  val valid = Bool()
  val bank = UInt(2.W)
  val addr = UInt(6.W)
  val data = UInt(64.W)
}

final class DADAOIntExecIO(
    val params: DADAOParams,
    val testMode: Boolean
) extends Bundle {
  val pc = Input(UInt(params.addrBits.W))
  val commit = Input(Bool())
  val decoded = Input(new DADAODecodedInstruction)
  val control = Input(new DADAOControlSignals)
  val regFile = Flipped(new DADAORegFileIO(params.addrBits))
  val execValid = Output(Bool())

  val extRead0Bank = Input(UInt(2.W))
  val extRead0Addr = Input(UInt(6.W))
  val extRead0Data = Output(UInt(64.W))
  val extRead1Bank = Input(UInt(2.W))
  val extRead1Addr = Input(UInt(6.W))
  val extRead1Data = Output(UInt(64.W))
  val extWrite = Input(new DADAOTestRegWrite)
  val blockWrite = Input(new DADAOBlockRegWrite)

  val testRegWrite = Option.when(testMode)(Input(new DADAOTestRegWrite))
  val debugReadBank =
    Option.when(testMode)(Input(UInt(2.W)))
  val debugReadAddr =
    Option.when(testMode)(Input(UInt(6.W)))
  val debugReadData =
    Option.when(testMode)(Output(UInt(64.W)))
}

final class DADAOIntExec(
    val params: DADAOParams = DADAOParams(),
    val testMode: Boolean = false
) extends Module {
  val io = IO(new DADAOIntExecIO(params, testMode))

  private val regFile = io.regFile
  private val alu = Module(new DADAOALU)
  private val entries = DADAOExecTable.entries

  private val matches = VecInit(
    entries.map(entry => io.decoded.id === entry.id.U(9.W))
  )
  private val descriptorValid = matches.asUInt.orR
  io.execValid := descriptorValid

  private def refValue(ref: DADAOExecRegRef): UInt =
    if (!ref.valid) 0.U(6.W)
    else io.decoded.word(ref.low + ref.width - 1, ref.low)

  private def selectRef(
      select: DADAOExecEntry => DADAOExecRegRef
  ): UInt =
    Mux1H(
      matches,
      entries.map(entry => refValue(select(entry)))
    )

  private def selectBank(
      select: DADAOExecEntry => DADAOExecRegRef
  ): UInt =
    Mux1H(
      matches,
      entries.map { entry =>
        val ref = select(entry)
        (if (ref.valid) ref.bank else 0).U(2.W)
      }
    )

  private def selectOperation: UInt =
    Mux1H(matches, entries.map(_.operation.U(5.W)))

  private def selectWidth: UInt =
    Mux1H(matches, entries.map(_.widthCode.U(2.W)))

  private def selectSigned: Bool =
    Mux1H(matches, entries.map(_.signed.B))

  private def selectDstCount: UInt =
    Mux1H(matches, entries.map(_.dstCount.U(2.W)))

  private def selectSrcCount: UInt =
    Mux1H(matches, entries.map(_.srcCount.U(2.W)))

  private def selectImmMode: UInt =
    Mux1H(matches, entries.map(_.immMode.U(3.W)))

  private def selectSpecial: UInt =
    Mux1H(matches, entries.map(_.special.U(2.W)))

  private def immediateRaw(entry: DADAOExecEntry): UInt =
    if (entry.immWidth == 0) 0.U(64.W)
    else {
      val raw = io.decoded.word(
        entry.immLow + entry.immWidth - 1,
        entry.immLow
      )
      zeroExtend(raw, entry.immWidth)
    }

  private def wydePosition(entry: DADAOExecEntry): UInt =
    if (entry.wydePosWidth == 0) 0.U(6.W)
    else {
      val raw = io.decoded.word(
        entry.wydePosLow + entry.wydePosWidth - 1,
        entry.wydePosLow
      )
      zeroExtend(raw, entry.wydePosWidth)
    }

  private def zeroExtend(value: UInt, width: Int): UInt =
    if (width == 64) value
    else Cat(0.U((64 - width).W), value)

  private def signExtend(value: UInt, width: Int): UInt =
    if (width == 64) value
    else Cat(Fill(64 - width, value(width - 1)), value)

  private def selectSourceValue(index: Int): UInt = {
    val refs = entries.map { entry =>
      index match {
        case 0 => entry.src0
        case 1 => entry.src1
        case _ => entry.src2
      }
    }
    Mux1H(matches, refs.map(refValue))
  }

  private val srcBanks = Seq.tabulate(3) { index =>
    Mux1H(
      matches,
      entries.map { entry =>
        val ref = index match {
          case 0 => entry.src0
          case 1 => entry.src1
          case _ => entry.src2
        }
        (if (ref.valid) ref.bank else 0).U(2.W)
      }
    )
  }

  private val dstBanks = Seq.tabulate(2) { index =>
    Mux1H(
      matches,
      entries.map { entry =>
        val ref = if (index == 0) entry.dst0 else entry.dst1
        (if (ref.valid) ref.bank else 0).U(2.W)
      }
    )
  }

  private val dstValues = Seq.tabulate(2) { index =>
    Mux1H(
      matches,
      entries.map { entry =>
        refValue(if (index == 0) entry.dst0 else entry.dst1)
      }
    )
  }

  private val selectedImmMode = selectImmMode
  private val selectedSpecial = selectSpecial
  private val selectedOperation = selectOperation
  private val selectedImmRaw = Mux1H(
    matches,
    entries.map(immediateRaw)
  )
  private val selectedWyde = Mux1H(
    matches,
    entries.map(wydePosition)
  )
  private val selectedImm = MuxLookup(
    selectedImmMode,
    0.U(64.W)
  )(
    Seq(
      DADAOExecImmMode.Immu6.U ->
        zeroExtend(selectedImmRaw(5, 0), 6),
      DADAOExecImmMode.Imms12.U ->
        signExtend(selectedImmRaw(11, 0), 12),
      DADAOExecImmMode.Immu12.U ->
        zeroExtend(selectedImmRaw(11, 0), 12),
      DADAOExecImmMode.Imms18.U ->
        signExtend(selectedImmRaw(17, 0), 18),
      DADAOExecImmMode.Immu16Wyde.U ->
        zeroExtend(selectedImmRaw(15, 0), 16)
    )
  )

  private def readAddress(
      bank: Int,
      index: Int
  ): UInt = {
    val selectors = entries.zip(matches).map { case (entry, matched) =>
      val ref = index match {
        case 0 => entry.src0
        case 1 => entry.src1
        case _ => entry.src2
      }
      matched &&
        ref.valid.B &&
        (if (ref.valid) ref.bank else 0).U === bank.U
    }
    Mux1H(selectors, entries.map { entry =>
      refValue(
        index match {
          case 0 => entry.src0
          case 1 => entry.src1
          case _ => entry.src2
        }
      )
    })
  }

  private def readValueFromBank(
      bank: UInt,
      rdValue: UInt,
      rbValue: UInt,
      raValue: UInt
  ): UInt =
    MuxLookup(bank, 0.U(64.W))(
      Seq(
        DADAORegBank.Rd.U -> rdValue,
        DADAORegBank.Rb.U -> rbValue,
        DADAORegBank.Ra.U -> raValue
      )
    )

  regFile.pc := io.pc
  regFile.blockWrite := io.blockWrite
  for (index <- 0 until 3) {
    regFile.rdReadAddr(index) :=
      readAddress(DADAORegBank.Rd, index)
    regFile.rbReadAddr(index) :=
      readAddress(DADAORegBank.Rb, index)
    regFile.raReadAddr(index) :=
      readAddress(DADAORegBank.Ra, index)
  }

  private val sourceValues = Seq.tabulate(3) { index =>
    readValueFromBank(
      srcBanks(index),
      regFile.rdReadData(index),
      regFile.rbReadData(index),
      regFile.raReadData(index)
    )
  }
  private val sourceFieldValues = Seq(
    selectRef(_.src0),
    selectRef(_.src1),
    selectRef(_.src2)
  )

  alu.io.operation := selectedOperation
  alu.io.widthCode := selectWidth
  alu.io.signed := selectSigned
  alu.io.dualResult := selectDstCount === 2.U
  alu.io.operandA := Mux(
    selectedOperation === DADAOExecOperation.AipSi.U,
    io.pc,
    sourceValues(0)
  )
  alu.io.operandB := Mux(
    selectedImmMode === DADAOExecImmMode.None.U,
    sourceValues(1),
    selectedImm
  )
  alu.io.operandC := sourceValues(1)
  alu.io.operandD := sourceValues(2)
  alu.io.auxIndex := Mux(
    selectedSpecial === DADAOExecSpecial.SetWyde.U,
    selectedWyde,
    selectedImmRaw(5, 0)
  )

  private val baseCommit =
    io.commit &&
      io.control.valid &&
      io.control.isM1 &&
      descriptorValid
  private val regularCommit =
    baseCommit &&
      selectedSpecial =/= DADAOExecSpecial.CopyBlock.U &&
      alu.io.validOp
  private val copyCommit =
    baseCommit &&
      selectedSpecial === DADAOExecSpecial.CopyBlock.U

  for (index <- 0 until 64) {
    regFile.rdWrite(index).valid := false.B
    regFile.rdWrite(index).bits := 0.U
    regFile.rbWrite(index).valid := false.B
    regFile.rbWrite(index).bits := 0.U
    regFile.raWrite(index).valid := false.B
    regFile.raWrite(index).bits := 0.U
  }

  private def writeRegister(
      bank: UInt,
      addr: UInt,
      data: UInt,
      enable: Bool
  ): Unit = {
    for (index <- 0 until 64) {
      when(enable && addr === index.U) {
        when(bank === DADAORegBank.Rd.U) {
          regFile.rdWrite(index).valid := true.B
          regFile.rdWrite(index).bits := data
        }.elsewhen(bank === DADAORegBank.Rb.U) {
          regFile.rbWrite(index).valid := true.B
          regFile.rbWrite(index).bits := data
        }.elsewhen(bank === DADAORegBank.Ra.U) {
          regFile.raWrite(index).valid := true.B
          regFile.raWrite(index).bits := data
        }
      }
    }
  }

  private val dualDestination = selectDstCount === 2.U
  writeRegister(
    dstBanks(0),
    dstValues(0),
    Mux(dualDestination, alu.io.resultHi, alu.io.resultLo),
    regularCommit && alu.io.primaryCommit
  )
  writeRegister(
    dstBanks(1),
    dstValues(1),
    alu.io.resultLo,
    regularCommit && alu.io.primaryCommit && dualDestination
  )

  regFile.bulkCopy.valid := copyCommit
  regFile.bulkCopy.sourceBank := srcBanks(0)
  regFile.bulkCopy.destBank := dstBanks(0)
  regFile.bulkCopy.sourceStart := sourceFieldValues(0)
  regFile.bulkCopy.destStart := dstValues(0)
  regFile.bulkCopy.count := selectedImmRaw(5, 0)

  val debugReadBank =
    if (testMode) io.debugReadBank.get else DADAORegBank.Rd.U
  val debugReadAddr =
    if (testMode) io.debugReadAddr.get else 0.U
  regFile.rdReadAddr(3) := Mux(
    io.extRead0Bank === DADAORegBank.Rd.U,
    io.extRead0Addr,
    0.U
  )
  regFile.rbReadAddr(3) := Mux(
    io.extRead0Bank === DADAORegBank.Rb.U,
    io.extRead0Addr,
    0.U
  )
  regFile.raReadAddr(3) := Mux(
    io.extRead0Bank === DADAORegBank.Ra.U,
    io.extRead0Addr,
    0.U
  )
  io.extRead0Data := readValueFromBank(
    io.extRead0Bank,
    regFile.rdReadData(3),
    regFile.rbReadData(3),
    regFile.raReadData(3)
  )

  regFile.rdReadAddr(4) := Mux(
    io.extRead1Bank === DADAORegBank.Rd.U,
    io.extRead1Addr,
    0.U
  )
  regFile.rbReadAddr(4) := Mux(
    io.extRead1Bank === DADAORegBank.Rb.U,
    io.extRead1Addr,
    0.U
  )
  regFile.raReadAddr(4) := Mux(
    io.extRead1Bank === DADAORegBank.Ra.U,
    io.extRead1Addr,
    0.U
  )
  io.extRead1Data := readValueFromBank(
    io.extRead1Bank,
    regFile.rdReadData(4),
    regFile.rbReadData(4),
    regFile.raReadData(4)
  )

  regFile.rdReadAddr(5) := Mux(
    debugReadBank === DADAORegBank.Rd.U,
    debugReadAddr,
    0.U
  )
  regFile.rbReadAddr(5) := Mux(
    debugReadBank === DADAORegBank.Rb.U,
    debugReadAddr,
    0.U
  )
  regFile.raReadAddr(5) := Mux(
    debugReadBank === DADAORegBank.Ra.U,
    debugReadAddr,
    0.U
  )

  if (testMode) {
    io.debugReadData.get := readValueFromBank(
      debugReadBank,
      regFile.rdReadData(5),
      regFile.rbReadData(5),
      regFile.raReadData(5)
    )

    writeRegister(
      io.testRegWrite.get.bank,
      io.testRegWrite.get.addr,
      io.testRegWrite.get.data,
      io.testRegWrite.get.valid
    )
  }

  writeRegister(
    io.extWrite.bank,
    io.extWrite.addr,
    io.extWrite.data,
    io.extWrite.valid
  )
}
