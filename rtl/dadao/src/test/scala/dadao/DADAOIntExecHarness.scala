package dadao

import chisel3._

final class DADAOIntExecHarnessIO(val params: DADAOParams) extends Bundle {
  val pc = Input(UInt(params.addrBits.W))
  val word = Input(UInt(32.W))
  val instructionId = Input(UInt(9.W))
  val commit = Input(Bool())
  val controlValid = Input(Bool())
  val controlIsM1 = Input(Bool())

  val testRegWrite = Input(new DADAOTestRegWrite)
  val extWrite = Input(new DADAOTestRegWrite)
  val debugReadBank = Input(UInt(2.W))
  val debugReadAddr = Input(UInt(6.W))
  val debugReadData = Output(UInt(64.W))
}

final class DADAOIntExecHarness(
    val params: DADAOParams = DADAOParams()
) extends Module {
  val io = IO(new DADAOIntExecHarnessIO(params))

  private val regFile = Module(new DADAORegFile(params))
  private val intExec = Module(new DADAOIntExec(params, testMode = true))

  intExec.io.regFile <> regFile.io
  regFile.rasControl.req.push := false.B
  regFile.rasControl.req.pushAddress := 0.U
  regFile.rasControl.req.pop := false.B
  regFile.rasControl.memReqAccepted := false.B
  regFile.rasControl.memResp.valid := false.B
  regFile.rasControl.memResp.data := 0.U
  regFile.rasControl.memResp.fault := false.B
  regFile.rasControl.memResp.faultCode := DADAOFaultCode.None.U

  intExec.io.pc := io.pc
  intExec.io.commit := io.commit
  intExec.io.decoded.word := io.word
  intExec.io.decoded.id := io.instructionId
  intExec.io.decoded.format := 0.U
  intExec.io.decoded.slot0 := 0.U
  intExec.io.decoded.slot1 := 0.U
  intExec.io.decoded.slot2 := 0.U
  intExec.io.decoded.slot3 := 0.U
  intExec.io.decoded.imm12 := 0.U
  intExec.io.decoded.imm18 := 0.U
  intExec.io.decoded.imm24 := 0.U

  intExec.io.control.valid := io.controlValid
  intExec.io.control.isM1 := io.controlIsM1
  intExec.io.control.scope := DADAOScope.M1.U
  intExec.io.control.isNoop := false.B
  intExec.io.control.fault := false.B
  intExec.io.control.faultCode := DADAOFaultCode.None.U
  intExec.io.control.debugFaultReason :=
    DADAODebugFaultReason.None.U
  intExec.io.control.unsupported := !io.controlIsM1

  intExec.io.extRead0Bank := DADAORegBank.Rd.U
  intExec.io.extRead0Addr := 0.U
  intExec.io.extRead1Bank := DADAORegBank.Rd.U
  intExec.io.extRead1Addr := 0.U
  intExec.io.extWrite := io.extWrite
  intExec.io.blockWrite := 0.U.asTypeOf(new DADAOBlockRegWrite)
  intExec.io.testRegWrite.get := io.testRegWrite
  intExec.io.debugReadBank.get := io.debugReadBank
  intExec.io.debugReadAddr.get := io.debugReadAddr
  io.debugReadData := intExec.io.debugReadData.get
}
