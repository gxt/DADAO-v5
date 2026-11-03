package dadao

import chisel3._
import chisel3.util._

final class DADAOTestMemoryHarnessIO(
    val params: DADAOParams,
    val maxEntries: Int
) extends Bundle {
  val load = Input(new DADAOTestMemoryLoad(params, maxEntries))
  val debugMemIndex =
    Input(UInt(math.max(1, log2Ceil(maxEntries)).W))
  val debugMemValid = Output(Bool())
  val debugMemAddress = Output(UInt(params.addrBits.W))
  val debugMemData = Output(UInt(params.dataBits.W))
  val debugMemWritable = Output(Bool())
  val debugMemFault = Output(Bool())
  val debugMemFaultCode = Output(UInt(8.W))
  val stats = Output(new DADAOTestMemoryStats)

  val pcInitValid = Input(Bool())
  val pcInit = Input(UInt(params.addrBits.W))
  val debugPc = Output(UInt(params.addrBits.W))
  val debugDecodedValid = Output(Bool())
  val debugWord = Output(UInt(32.W))
  val debugId = Output(UInt(9.W))
  val debugFormat = Output(UInt(4.W))
  val debugScope = Output(UInt(2.W))
  val debugNoop = Output(Bool())
  val debugFault = Output(Bool())
  val debugFaultCode = Output(UInt(8.W))
  val debugFaultReason = Output(UInt(3.W))

  val testRegWrite = Input(new DADAOTestRegWrite)
  val debugRegBank = Input(UInt(2.W))
  val debugRegAddr = Input(UInt(6.W))
  val debugRegData = Output(UInt(64.W))
  val debugDataRequestAddr = Output(UInt(params.addrBits.W))
  val debugDataRequestWrite = Output(Bool())
  val debugDataRequestWdata = Output(UInt(64.W))
  val debugDataRequestWstrb = Output(UInt(8.W))
  val debugDataResponseData = Output(UInt(64.W))
  val debugLoadWrite = Output(Bool())
  val debugLoadWriteData = Output(UInt(64.W))
  val testCfxWrite = Input(new DADAOCfxTestWrite)
  val testCfxStatusSet = Input(new DADAOCfxStatusSet)
  val debugCfxRead = Input(new DADAOCfxTestRead)
  val debugCfxReadData = Output(UInt(64.W))
  val debugCfxReadValid = Output(Bool())
  val debugCfxStatus = Output(new DADAOCfxStatus)
}

final class DADAOTestMemoryHarness(
    val params: DADAOParams = DADAOParams(),
    val maxEntries: Int = 64,
    val reqReadyDelay: Int = 0,
    val memRespLatency: Int = 0
) extends Module {
  val io = IO(new DADAOTestMemoryHarnessIO(params, maxEntries))

  private val core = Module(new DADAOCore(params, testMode = true))
  private val memory = Module(
    new DADAOTestMemory(
      params,
      maxEntries,
      reqReadyDelay,
      memRespLatency
    )
  )

  core.io.mem.req <> memory.io.req
  memory.io.resp <> core.io.mem.resp

  core.io.pcInitValid.get := io.pcInitValid
  core.io.pcInit.get := io.pcInit

  io.load <> memory.io.load
  memory.io.debugPeekIndex := io.debugMemIndex
  io.debugMemValid := memory.io.debugPeek.valid
  io.debugMemAddress := memory.io.debugPeek.address
  io.debugMemData := memory.io.debugPeek.data
  io.debugMemWritable := memory.io.debugPeek.writable
  io.debugMemFault := memory.io.debugPeek.fault
  io.debugMemFaultCode := memory.io.debugPeek.faultCode
  io.stats := memory.io.stats

  io.debugPc := core.io.debugPc.get
  io.debugDecodedValid := core.io.debugDecodedValid.get
  io.debugWord := core.io.debugWord.get
  io.debugId := core.io.debugId.get
  io.debugFormat := core.io.debugFormat.get
  io.debugScope := core.io.debugScope.get
  io.debugNoop := core.io.debugNoop.get
  io.debugFault := core.io.debugFault.get
  io.debugFaultCode := core.io.debugFaultCode.get
  io.debugFaultReason := core.io.debugFaultReason.get
  core.io.testRegWrite.get := io.testRegWrite
  core.io.debugRegBank.get := io.debugRegBank
  core.io.debugRegAddr.get := io.debugRegAddr
  io.debugRegData := core.io.debugRegData.get
  io.debugDataRequestAddr := core.io.debugDataRequestAddr.get
  io.debugDataRequestWrite := core.io.debugDataRequestWrite.get
  io.debugDataRequestWdata := core.io.debugDataRequestWdata.get
  io.debugDataRequestWstrb := core.io.debugDataRequestWstrb.get
  io.debugDataResponseData := core.io.debugDataResponseData.get
  io.debugLoadWrite := core.io.debugLoadWrite.get
  io.debugLoadWriteData := core.io.debugLoadWriteData.get
  core.io.testCfxWrite.get := io.testCfxWrite
  core.io.testCfxStatusSet.get := io.testCfxStatusSet
  core.io.debugCfxRead.get := io.debugCfxRead
  io.debugCfxReadData := core.io.debugCfxReadData.get
  io.debugCfxReadValid := core.io.debugCfxReadValid.get
  io.debugCfxStatus := core.io.debugCfxStatus.get
}
