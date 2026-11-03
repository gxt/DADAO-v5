package dadao

import chisel3._

final class DADAOCpuTopIO(
    val params: DADAOParams,
    val testMode: Boolean
) extends Bundle {
  val pc = Output(UInt(params.addrBits.W))
  val pcInitValid =
    Option.when(testMode)(Input(Bool()))
  val pcInit =
    Option.when(testMode)(Input(UInt(params.addrBits.W)))
  val testRegWrite =
    Option.when(testMode)(Input(new DADAOTestRegWrite))
  val debugRegBank =
    Option.when(testMode)(Input(UInt(2.W)))
  val debugRegAddr =
    Option.when(testMode)(Input(UInt(6.W)))
  val debugRegData =
    Option.when(testMode)(Output(UInt(64.W)))
  val debugPc =
    Option.when(testMode)(Output(UInt(params.addrBits.W)))
  val debugDecodedValid =
    Option.when(testMode)(Output(Bool()))
  val debugWord =
    Option.when(testMode)(Output(UInt(32.W)))
  val debugId =
    Option.when(testMode)(Output(UInt(9.W)))
  val debugFault =
    Option.when(testMode)(Output(Bool()))
  val debugFaultCode =
    Option.when(testMode)(Output(UInt(8.W)))
  val debugDataRequestAddr =
    Option.when(testMode)(Output(UInt(params.addrBits.W)))
  val debugDataRequestWrite =
    Option.when(testMode)(Output(Bool()))
  val debugDataRequestWdata =
    Option.when(testMode)(Output(UInt(64.W)))
  val debugDataRequestWstrb =
    Option.when(testMode)(Output(UInt(8.W)))
  val debugDataResponseData =
    Option.when(testMode)(Output(UInt(64.W)))
  val debugLoadWrite =
    Option.when(testMode)(Output(Bool()))
  val debugLoadWriteData =
    Option.when(testMode)(Output(UInt(64.W)))
}

final class DADAOCpuTop(
    val params: DADAOParams = DADAOParams(),
    val testMode: Boolean = false,
    val romContents: Seq[BigInt] = DADAOCpuTop.defaultRomContents
) extends Module {
  val io = IO(new DADAOCpuTopIO(params, testMode))

  private val core = Module(new DADAOCore(params, testMode))
  private val adapter = Module(new DADAOTLAdapter(params))
  private val xbar = Module(new DADAOTLXbar(params))
  private val rom = Module(new DADAOTLROM(params, romContents))
  private val ram = Module(new DADAOTLRAM(params))

  adapter.io.core <> core.io.mem
  xbar.io.in <> adapter.io.tl
  rom.io.tl <> xbar.io.rom
  ram.io.tl <> xbar.io.ram

  io.pc := core.io.pc
  if (testMode) {
    core.io.pcInitValid.get := io.pcInitValid.get
    core.io.pcInit.get := io.pcInit.get
    core.io.testRegWrite.get := io.testRegWrite.get
    core.io.debugRegBank.get := io.debugRegBank.get
    core.io.debugRegAddr.get := io.debugRegAddr.get
    core.io.testCfxWrite.get :=
      0.U.asTypeOf(new DADAOCfxTestWrite)
    core.io.testCfxStatusSet.get :=
      0.U.asTypeOf(new DADAOCfxStatusSet)
    core.io.debugCfxRead.get :=
      0.U.asTypeOf(new DADAOCfxTestRead)
    io.debugRegData.get := core.io.debugRegData.get
    io.debugPc.get := core.io.debugPc.get
    io.debugDecodedValid.get := core.io.debugDecodedValid.get
    io.debugWord.get := core.io.debugWord.get
    io.debugId.get := core.io.debugId.get
    io.debugFault.get := core.io.debugFault.get
    io.debugFaultCode.get := core.io.debugFaultCode.get
    io.debugDataRequestAddr.get := core.io.debugDataRequestAddr.get
    io.debugDataRequestWrite.get := core.io.debugDataRequestWrite.get
    io.debugDataRequestWdata.get := core.io.debugDataRequestWdata.get
    io.debugDataRequestWstrb.get := core.io.debugDataRequestWstrb.get
    io.debugDataResponseData.get := core.io.debugDataResponseData.get
    io.debugLoadWrite.get := core.io.debugLoadWrite.get
    io.debugLoadWriteData.get := core.io.debugLoadWriteData.get
  }
}

object DADAOCpuTop {
  val defaultRomContents: Seq[BigInt] = Seq(
    DADAOTLEndian.reverseBeatValue(
      BigInt("4788000047880000", 16)
    )
  )
}
