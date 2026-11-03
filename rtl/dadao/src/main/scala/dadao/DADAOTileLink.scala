package dadao

import chisel3._
import chisel3.util.{Cat, Decoupled, MuxLookup, log2Ceil}

final case class DADAOTLParams(
    addrBits: Int = 64,
    dataBits: Int = 64,
    sourceBits: Int = 1,
    sinkBits: Int = 1
) {
  require(dataBits == 64, "DADAO TileLink requires a 64-bit data beat")
  require(dataBits / 8 == DADAOByteLane.BeatBytes)
}

object DADAOTLMessages {
  val PutFullData: Int = 0
  val PutPartialData: Int = 1
  val Get: Int = 4
  val AccessAck: Int = 0
  val AccessAckData: Int = 1
}

object DADAOTLEndian {
  def reverseBeat(data: UInt): UInt =
    Cat((0 until DADAOByteLane.BeatBytes).map { index =>
      data(index * 8 + 7, index * 8)
    })

  def reverseMask(mask: UInt): UInt =
    mask

  def reverseBeatValue(data: BigInt): BigInt = {
    var result = BigInt(0)
    for (index <- 0 until DADAOByteLane.BeatBytes) {
      result = (result << 8) | ((data >> (index * 8)) & 0xff)
    }
    result
  }
}

final class DADAOTLARequest(
    val params: DADAOTLParams
) extends Bundle {
  val opcode = UInt(3.W)
  val param = UInt(3.W)
  val size = UInt(3.W)
  val source = UInt(params.sourceBits.W)
  val address = UInt(params.addrBits.W)
  val mask = UInt(DADAOByteLane.BeatBytes.W)
  val data = UInt(params.dataBits.W)
  val corrupt = Bool()
}

final class DADAOTLDResponse(
    val params: DADAOTLParams
) extends Bundle {
  val opcode = UInt(3.W)
  val param = UInt(3.W)
  val size = UInt(3.W)
  val source = UInt(params.sourceBits.W)
  val sink = UInt(params.sinkBits.W)
  val denied = Bool()
  val corrupt = Bool()
  val data = UInt(params.dataBits.W)
}

final class DADAOTLMasterIO(
    val params: DADAOTLParams
) extends Bundle {
  val a = Decoupled(new DADAOTLARequest(params))
  val d = Flipped(Decoupled(new DADAOTLDResponse(params)))
}

final class DADAOTLManagerIO(
    val params: DADAOTLParams
) extends Bundle {
  val a = Flipped(Decoupled(new DADAOTLARequest(params)))
  val d = Decoupled(new DADAOTLDResponse(params))
}

final class DADAOTLAdapterIO(
    val params: DADAOParams
) extends Bundle {
  val core = Flipped(
    new DADAOMemPort(params.addrBits, params.dataBits)
  )
  val tl = new DADAOTLMasterIO(DADAOTLParams(params.addrBits))
}

private[dadao] object DADAOTLAdapterState {
  val Idle: Int = 0
  val Send: Int = 1
  val WaitResponse: Int = 2
}

final class DADAOTLAdapter(
    val params: DADAOParams = DADAOParams()
) extends Module {
  val io = IO(new DADAOTLAdapterIO(params))

  private val state =
    RegInit(DADAOTLAdapterState.Idle.U(2.W))
  private val held =
    RegInit(
      0.U.asTypeOf(new DADAOMemReq(params.addrBits, params.dataBits))
    )

  private val addressLow = held.addr(2, 0)
  private val guestMask =
    held.wstrb
  private val guestBeat =
    DADAOByteLane.mergeWrite(
      0.U(64.W),
      held.wdata,
      addressLow,
      held.size,
      held.wstrb
    )
  private val expectAccessAckData = !held.write

  io.core.req.ready := state === DADAOTLAdapterState.Idle.U
  io.tl.a.valid := state === DADAOTLAdapterState.Send.U
  io.tl.a.bits.opcode :=
    Mux(
      held.write,
      Mux(
        held.size === DADAOMemSize.Octa.U,
        DADAOTLMessages.PutFullData.U,
        DADAOTLMessages.PutPartialData.U
      ),
      DADAOTLMessages.Get.U
    )
  io.tl.a.bits.param := 0.U
  io.tl.a.bits.size := held.size
  io.tl.a.bits.source := 0.U
  io.tl.a.bits.address := held.addr
  io.tl.a.bits.mask := DADAOTLEndian.reverseMask(guestMask)
  io.tl.a.bits.data := DADAOTLEndian.reverseBeat(guestBeat)
  io.tl.a.bits.corrupt := false.B

  io.tl.d.ready :=
    state === DADAOTLAdapterState.WaitResponse.U &&
      io.core.resp.ready
  io.core.resp.valid :=
    state === DADAOTLAdapterState.WaitResponse.U &&
      io.tl.d.valid

  private val responseOpcodeFault =
    Mux(
      expectAccessAckData,
      io.tl.d.bits.opcode =/= DADAOTLMessages.AccessAckData.U,
      io.tl.d.bits.opcode =/= DADAOTLMessages.AccessAck.U
    )
  private val responseFault =
    io.tl.d.bits.denied ||
      io.tl.d.bits.corrupt ||
      responseOpcodeFault
  io.core.resp.bits.rdata :=
    Mux(
      responseFault,
      0.U,
      DADAOByteLane.readValue(
        DADAOTLEndian.reverseBeat(io.tl.d.bits.data),
        addressLow,
        held.size
      )
    )
  io.core.resp.bits.fault := responseFault
  io.core.resp.bits.faultCode :=
    Mux(
      responseFault,
      DADAOFaultCode.Illi.U,
      DADAOFaultCode.None.U
    )

  when(io.core.req.fire) {
    held := io.core.req.bits
    state := DADAOTLAdapterState.Send.U
  }.elsewhen(
    state === DADAOTLAdapterState.Send.U &&
      io.tl.a.ready
  ) {
    state := DADAOTLAdapterState.WaitResponse.U
  }.elsewhen(
    state === DADAOTLAdapterState.WaitResponse.U &&
      io.tl.d.valid &&
      io.core.resp.ready
  ) {
    state := DADAOTLAdapterState.Idle.U
  }
}

final class DADAOTLXbarIO(
    val params: DADAOTLParams
) extends Bundle {
  val in = Flipped(new DADAOTLMasterIO(params))
  val rom = new DADAOTLMasterIO(params)
  val ram = new DADAOTLMasterIO(params)
}

final class DADAOTLXbar(
    val dadaoParams: DADAOParams = DADAOParams()
) extends Module {
  private val tlParams = DADAOTLParams(dadaoParams.addrBits)
  val io = IO(new DADAOTLXbarIO(tlParams))

  private def inside(base: BigInt, extent: BigInt): Bool = {
    val addressExt = Cat(0.U(1.W), io.in.a.bits.address)
    val bytesExt = Cat(
      0.U((dadaoParams.addrBits - 3).W),
      DADAOByteLane.sizeBytes(io.in.a.bits.size)
    )
    val end = addressExt + bytesExt
    val start = base.U((dadaoParams.addrBits + 1).W)
    val limit = (base + extent).U((dadaoParams.addrBits + 1).W)
    addressExt >= start && end <= limit
  }

  private val romHit =
    inside(dadaoParams.bootRomBase, dadaoParams.bootRomSize)
  private val ramHit =
    inside(dadaoParams.ramBase, dadaoParams.ramSize)
  private val validTarget = romHit || ramHit
  private val locked = RegInit(false.B)
  private val selectedRom = RegInit(false.B)
  private val errorPending = RegInit(false.B)
  private val errorResponse =
    RegInit(0.U.asTypeOf(new DADAOTLDResponse(tlParams)))

  io.in.a.ready :=
    !locked &&
      !errorPending &&
      Mux(
        validTarget,
        Mux(romHit, io.rom.a.ready, io.ram.a.ready),
        true.B
      )

  io.rom.a.valid :=
    io.in.a.valid && !locked && !errorPending && romHit
  io.ram.a.valid :=
    io.in.a.valid && !locked && !errorPending && ramHit
  io.rom.a.bits := io.in.a.bits
  io.ram.a.bits := io.in.a.bits

  private val selectedResponse =
    Mux(selectedRom, io.rom.d.bits, io.ram.d.bits)
  private val selectedResponseValid =
    Mux(selectedRom, io.rom.d.valid, io.ram.d.valid)
  io.in.d.valid :=
    errorPending || (locked && selectedResponseValid)
  io.in.d.bits :=
    Mux(errorPending, errorResponse, selectedResponse)
  io.rom.d.ready :=
    locked && selectedRom && io.in.d.ready
  io.ram.d.ready :=
    locked && !selectedRom && io.in.d.ready

  when(io.in.a.fire) {
    when(validTarget) {
      locked := true.B
      selectedRom := romHit
    }.otherwise {
      errorPending := true.B
      errorResponse.opcode :=
        Mux(
          io.in.a.bits.opcode === DADAOTLMessages.Get.U,
          DADAOTLMessages.AccessAckData.U,
          DADAOTLMessages.AccessAck.U
        )
      errorResponse.param := 0.U
      errorResponse.size := io.in.a.bits.size
      errorResponse.source := io.in.a.bits.source
      errorResponse.sink := 0.U
      errorResponse.denied := true.B
      errorResponse.corrupt := false.B
      errorResponse.data := 0.U
    }
  }

  when(io.in.d.fire) {
    when(errorPending) {
      errorPending := false.B
    }.otherwise {
      locked := false.B
    }
  }
}

final class DADAOTLROM(
    val params: DADAOParams,
    val contents: Seq[BigInt]
) extends Module {
  require(contents.nonEmpty, "TL ROM requires at least one data beat")
  require(
    contents.size <= (params.bootRomSize / DADAOByteLane.BeatBytes).toInt,
    "TL ROM contents exceed the frozen BootROM size"
  )

  private val tlParams = DADAOTLParams(params.addrBits)
  val io = IO(new Bundle {
    val tl = new DADAOTLManagerIO(tlParams)
  })

  private val pending = RegInit(false.B)
  private val latchedSource =
    RegInit(0.U(tlParams.sourceBits.W))
  private val latchedSize = RegInit(0.U(3.W))
  private val latchedAddress =
    RegInit(0.U(params.addrBits.W))
  private val latchedWrite = RegInit(false.B)
  private val indexBits = math.max(1, log2Ceil(contents.size))
  private val rom = VecInit(
    contents.map(_.U(params.dataBits.W))
  )

  io.tl.a.ready := !pending
  io.tl.d.valid := pending
  io.tl.d.bits.opcode :=
    Mux(
      latchedWrite,
      DADAOTLMessages.AccessAck.U,
      DADAOTLMessages.AccessAckData.U
    )
  io.tl.d.bits.param := 0.U
  io.tl.d.bits.size := latchedSize
  io.tl.d.bits.source := latchedSource
  io.tl.d.bits.sink := 0.U
  io.tl.d.bits.denied := latchedWrite
  io.tl.d.bits.corrupt := false.B

  private val wordIndex =
    ((latchedAddress - params.bootRomBase.U) >>
      log2Ceil(DADAOByteLane.BeatBytes))(indexBits - 1, 0)
  private val romIndex =
    if (contents.size == 1) 0.U else wordIndex
  io.tl.d.bits.data :=
    Mux(
      latchedWrite || wordIndex >= contents.size.U,
      0.U,
      rom(romIndex)
    )

  when(io.tl.a.fire) {
    pending := true.B
    latchedSource := io.tl.a.bits.source
    latchedSize := io.tl.a.bits.size
    latchedAddress := io.tl.a.bits.address
    latchedWrite :=
      io.tl.a.bits.opcode =/= DADAOTLMessages.Get.U
  }.elsewhen(io.tl.d.fire) {
    pending := false.B
  }
}

final class DADAOTLRAM(
    val params: DADAOParams
) extends Module {
  private val tlParams = DADAOTLParams(params.addrBits)
  val io = IO(new Bundle {
    val tl = new DADAOTLManagerIO(tlParams)
  })

  private val words = (params.ramSize / DADAOByteLane.BeatBytes).toInt
  private val mem = SyncReadMem(words, UInt(params.dataBits.W))
  private val pending = RegInit(false.B)
  private val latchedSource =
    RegInit(0.U(tlParams.sourceBits.W))
  private val latchedSize = RegInit(0.U(3.W))
  private val latchedAddress =
    RegInit(0.U(params.addrBits.W))
  private val latchedMask =
    RegInit(0.U(DADAOByteLane.BeatBytes.W))
  private val latchedData = RegInit(0.U(params.dataBits.W))
  private val latchedWrite = RegInit(false.B)

  private val currentIndex =
    (io.tl.a.bits.address - params.ramBase.U) >>
      log2Ceil(DADAOByteLane.BeatBytes)
  private val readData =
    mem.read(currentIndex, io.tl.a.valid && io.tl.a.ready)
  private val latchedIndex =
    (latchedAddress - params.ramBase.U) >>
      log2Ceil(DADAOByteLane.BeatBytes)
  private def mergeLanes(oldData: UInt, newData: UInt, mask: UInt): UInt =
    Cat((0 until DADAOByteLane.BeatBytes).map { index =>
      val lane = DADAOByteLane.BeatBytes - 1 - index
      Mux(
        mask(lane),
        newData(lane * 8 + 7, lane * 8),
        oldData(lane * 8 + 7, lane * 8)
      )
    })

  private val mergedData =
    mergeLanes(readData, latchedData, latchedMask)

  io.tl.a.ready := !pending
  io.tl.d.valid := pending
  io.tl.d.bits.opcode :=
    Mux(
      latchedWrite,
      DADAOTLMessages.AccessAck.U,
      DADAOTLMessages.AccessAckData.U
    )
  io.tl.d.bits.param := 0.U
  io.tl.d.bits.size := latchedSize
  io.tl.d.bits.source := latchedSource
  io.tl.d.bits.sink := 0.U
  io.tl.d.bits.denied := false.B
  io.tl.d.bits.corrupt := false.B
  io.tl.d.bits.data := Mux(latchedWrite, 0.U, readData)

  when(io.tl.a.fire) {
    pending := true.B
    latchedSource := io.tl.a.bits.source
    latchedSize := io.tl.a.bits.size
    latchedAddress := io.tl.a.bits.address
    latchedMask := io.tl.a.bits.mask
    latchedData := io.tl.a.bits.data
    latchedWrite :=
      io.tl.a.bits.opcode === DADAOTLMessages.PutFullData.U ||
        io.tl.a.bits.opcode === DADAOTLMessages.PutPartialData.U
  }.elsewhen(pending && latchedWrite) {
    mem.write(latchedIndex, mergedData)
  }

  when(io.tl.d.fire) {
    pending := false.B
  }
}
