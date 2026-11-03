package dadao

import chisel3._
import chisel3.util.{Cat, Valid}

final class DADAORasReq extends Bundle {
  val push = Bool()
  val pushAddress = UInt(48.W)
  val pop = Bool()
}

final class DADAORasMemResp extends Bundle {
  val valid = Bool()
  val data = UInt(64.W)
  val fault = Bool()
  val faultCode = UInt(8.W)
}

final class DADAORasResp(
    val addrBits: Int = 64
) extends Bundle {
  val popAddress = UInt(48.W)
  val fault = Bool()
  val faultCode = UInt(8.W)
  val done = Bool()
  val state = UInt(2.W)
  val memStart = Bool()
  val raCnt = UInt(6.W)
  val mrPtr = UInt(48.W)
  val memReqValid = Bool()
  val memReqWrite = Bool()
  val memReqAddr = UInt(addrBits.W)
  val memReqWdata = UInt(64.W)
}

final class DADAORasIO(
    val params: DADAOParams
) extends Bundle {
  val write = Input(Vec(64, Valid(UInt(64.W))))
  val req = Input(new DADAORasReq)
  val memReqAccepted = Input(Bool())
  val memResp = Input(new DADAORasMemResp)
  val resp = Output(new DADAORasResp(params.addrBits))
  val values = Output(Vec(64, UInt(64.W)))
}

final class DADAORasControlIO(
    val params: DADAOParams
) extends Bundle {
  val req = Input(new DADAORasReq)
  val memReqAccepted = Input(Bool())
  val memResp = Input(new DADAORasMemResp)
  val resp = Output(new DADAORasResp(params.addrBits))
}

private[dadao] object DADAORasState {
  val Idle: Int = 0
  val WaitAccept: Int = 1
  val WaitResponse: Int = 2
}

final class DADAORas(
    val params: DADAOParams = DADAOParams()
) extends Module {
  val io = IO(new DADAORasIO(params))

  private val raRegs =
    RegInit(VecInit(Seq.fill(64)(0.U(64.W))))
  private val state = RegInit(DADAORasState.Idle.U(2.W))
  private val memAddress = RegInit(0.U(48.W))
  private val memWrite = RegInit(false.B)
  private val memWdata = RegInit(0.U(64.W))
  private val pendingPushAddress = RegInit(0.U(48.W))

  private val raCnt = raRegs(0)(53, 48)
  private val mrPtr = raRegs(0)(47, 0)
  private val topCount = raRegs(63)(63, 48)
  private val topAddress = raRegs(63)(47, 0)

  private val startPush = io.req.push && !io.req.pop
  private val startPop = io.req.pop && !io.req.push
  private val startBoth = io.req.push && io.req.pop
  private val startAny = startPush || startPop || startBoth

  private val recursiveTop =
    raCnt =/= 0.U &&
      topAddress === io.req.pushAddress &&
      topCount < 0xffff.U
  private val spillNeeded =
    startPush &&
      raCnt === 63.U &&
      !recursiveTop &&
      mrPtr =/= 0.U
  private val restoreNeeded =
    startPop &&
      raCnt === 0.U &&
      mrPtr =/= 0.U

  private val previewAddress = Mux(spillNeeded, mrPtr - 8.U, mrPtr)
  private val previewWrite = spillNeeded
  private val memAccessCheck = Module(new DADAOAccessCheck(params))
  memAccessCheck.io.addr :=
    Cat(0.U((params.addrBits - 48).W), previewAddress)
  memAccessCheck.io.write := previewWrite
  memAccessCheck.io.size := DADAOMemSize.Octa.U
  memAccessCheck.io.kind := DADAOMemKind.Data.U

  private val startNeedsMem =
    spillNeeded || restoreNeeded
  private val startMemFault =
    startNeedsMem && memAccessCheck.io.fault
  private val startImmediateFault =
    startBoth ||
      (startPush && raCnt === 63.U && !recursiveTop && mrPtr === 0.U) ||
      (startPop && raCnt === 0.U && mrPtr === 0.U) ||
      (startPop && raCnt =/= 0.U && topCount === 0.U)
  private val startDone =
    state === DADAORasState.Idle.U &&
      startAny &&
      (!startNeedsMem || startMemFault)
  private val memoryDone =
    state === DADAORasState.WaitResponse.U &&
      io.memResp.valid
  private val memoryReadRasuf =
    memoryDone &&
      !memWrite &&
      !io.memResp.fault &&
      io.memResp.data(63, 48) === 0.U

  private val normalPopAddress = Mux(
    startPop && raCnt =/= 0.U && topCount =/= 0.U,
    topAddress,
    0.U
  )
  private val memoryPopAddress = Mux(
    memoryDone &&
      !io.memResp.fault &&
      !memWrite &&
      io.memResp.data(63, 48) =/= 0.U,
    io.memResp.data(47, 0),
    0.U
  )

  io.values := raRegs
  io.resp.popAddress :=
    Mux(memoryDone, memoryPopAddress, normalPopAddress)
  io.resp.done := startDone || memoryDone
  io.resp.state := state
  io.resp.memStart :=
    state === DADAORasState.Idle.U &&
      startAny &&
      startNeedsMem &&
      !startMemFault
  io.resp.raCnt := raCnt
  io.resp.mrPtr := mrPtr
  io.resp.memReqValid :=
    state === DADAORasState.WaitAccept.U
  io.resp.memReqWrite := memWrite
  io.resp.memReqAddr :=
    Cat(0.U((params.addrBits - 48).W), memAddress)
  io.resp.memReqWdata := memWdata

  io.resp.fault :=
    (startDone && (startImmediateFault || startMemFault)) ||
      (memoryDone && io.memResp.fault) ||
      memoryReadRasuf
  io.resp.faultCode := Mux(
    memoryDone && io.memResp.fault,
    io.memResp.faultCode,
    Mux(
      memoryReadRasuf,
      DADAOFaultCode.Rasuf.U,
      Mux(
        startMemFault,
        memAccessCheck.io.faultCode,
        Mux(
          startBoth,
          DADAOFaultCode.Illi.U,
          Mux(
            startPop && raCnt === 0.U,
            DADAOFaultCode.Rasuf.U,
            Mux(
              startPop && topCount === 0.U,
              DADAOFaultCode.Rasuf.U,
              Mux(
                startPush && raCnt === 63.U,
                DADAOFaultCode.Rasof.U,
                DADAOFaultCode.None.U
              )
            )
          )
        )
      )
    )
  )

  for (index <- 0 until 64) {
    when(
      io.write(index).valid &&
        state === DADAORasState.Idle.U
    ) {
      if (index == 0) {
        raRegs(index) :=
          Cat(0.U(10.W), io.write(index).bits(53, 0))
      } else {
        raRegs(index) := io.write(index).bits
      }
    }
  }

  when(state === DADAORasState.Idle.U && startAny) {
    when(startBoth) {
      // Precise fault: no architectural or memory state changes.
    }.elsewhen(startPush) {
      when(raCnt === 0.U) {
        raRegs(63) := Cat(1.U(16.W), io.req.pushAddress)
        raRegs(0) := Cat(0.U(10.W), 1.U(6.W), mrPtr)
      }.elsewhen(recursiveTop) {
        raRegs(63) :=
          (topCount + 1.U) ## io.req.pushAddress
      }.elsewhen(raCnt < 63.U) {
        for (index <- 1 until 63) {
          raRegs(index) := raRegs(index + 1)
        }
        raRegs(63) :=
          Cat(1.U(16.W), io.req.pushAddress)
        raRegs(0) :=
          Cat(0.U(10.W), (raCnt + 1.U)(5, 0), mrPtr)
      }.elsewhen(mrPtr === 0.U) {
        // RASOF, no state changes.
      }.elsewhen(memAccessCheck.io.fault) {
        // MemRAS address or permission fault, no state changes.
      }.otherwise {
        state := DADAORasState.WaitAccept.U
        memAddress := mrPtr - 8.U
        memWrite := true.B
        memWdata := raRegs(1)
        pendingPushAddress := io.req.pushAddress
      }
    }.elsewhen(startPop) {
      when(raCnt === 0.U && mrPtr === 0.U) {
        // RASUF, no state changes.
      }.elsewhen(raCnt === 0.U) {
        when(memAccessCheck.io.fault) {
          // MemRAS address or permission fault, no state changes.
        }.otherwise {
          state := DADAORasState.WaitAccept.U
          memAddress := mrPtr
          memWrite := false.B
          memWdata := 0.U
        }
      }.elsewhen(topCount === 0.U) {
        // RASUF, no state changes.
      }.elsewhen(topCount > 1.U) {
        raRegs(63) := (topCount - 1.U) ## topAddress
      }.otherwise {
        for (index <- 63 to 2 by -1) {
          raRegs(index) := raRegs(index - 1)
        }
        raRegs(1) := 0.U
        raRegs(0) :=
          Cat(0.U(10.W), (raCnt - 1.U)(5, 0), mrPtr)
      }
    }
  }

  when(
    state === DADAORasState.WaitAccept.U &&
      io.memReqAccepted
  ) {
    state := DADAORasState.WaitResponse.U
  }

  when(memoryDone) {
    state := DADAORasState.Idle.U
    when(!io.memResp.fault) {
      when(memWrite) {
        for (index <- 1 until 63) {
          raRegs(index) := raRegs(index + 1)
        }
        raRegs(63) :=
          Cat(1.U(16.W), pendingPushAddress)
        raRegs(0) :=
          Cat(0.U(10.W), 63.U(6.W), memAddress)
      }.elsewhen(io.memResp.data(63, 48) === 0.U) {
        // D4b-count0: RASUF; MRPTR and RA remain unchanged.
      }.elsewhen(io.memResp.data(63, 48) === 1.U) {
        raRegs(0) :=
          Cat(0.U(10.W), 0.U(6.W), memAddress + 8.U)
      }.otherwise {
        raRegs(63) :=
          (io.memResp.data(63, 48) - 1.U) ##
            io.memResp.data(47, 0)
        raRegs(0) :=
          Cat(0.U(10.W), 1.U(6.W), memAddress + 8.U)
      }
    }
  }
}
