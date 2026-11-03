package dadao

import chisel3._
import chisel3.util._

final class DADAOTestMemoryEntry(
    val addrBits: Int,
    val dataBits: Int
) extends Bundle {
  val valid = Bool()
  // Canonical address of the aligned 8-byte beat.
  val address = UInt(addrBits.W)
  // Big-endian 8-byte beat: byte 0 occupies bits[63:56].
  val data = UInt(dataBits.W)
  val writable = Bool()
  val fault = Bool()
  val faultCode = UInt(8.W)
}

final class DADAOTestMemoryLoad(
    val params: DADAOParams,
    val maxEntries: Int
) extends Bundle {
  val valid = Bool()
  val index = UInt(math.max(1, log2Ceil(maxEntries)).W)
  val address = UInt(params.addrBits.W)
  val data = UInt(params.dataBits.W)
  val writable = Bool()
  val fault = Bool()
  val faultCode = UInt(8.W)
}

final class DADAOTestMemoryStats extends Bundle {
  val requestCount = UInt(32.W)
  val responseCount = UInt(32.W)
  val writeCount = UInt(32.W)
  val faultCount = UInt(32.W)
  val unmappedCount = UInt(32.W)
}

final class DADAOTestMemoryIO(
    val params: DADAOParams,
    val maxEntries: Int
) extends Bundle {
  val req = Flipped(
    Decoupled(new DADAOMemReq(params.addrBits, params.dataBits))
  )
  val resp = Decoupled(
    new DADAOMemResp(params.dataBits)
  )
  val load = Input(new DADAOTestMemoryLoad(params, maxEntries))
  val debugPeekIndex =
    Input(UInt(math.max(1, log2Ceil(maxEntries)).W))
  val debugPeek = Output(
    new DADAOTestMemoryEntry(params.addrBits, params.dataBits)
  )
  val stats = Output(new DADAOTestMemoryStats)
}

/**
  * Sparse testbench memory model.
  *
  * This module is test-only. It models a finite vector table instead of
  * allocating the full architectural RAM window.
  */
final class DADAOTestMemory(
    val params: DADAOParams = DADAOParams(),
    val maxEntries: Int = 64,
    val reqReadyDelay: Int = 0,
    val memRespLatency: Int = 0
) extends Module {
  require(maxEntries > 0, "test memory requires at least one entry")
  require(reqReadyDelay >= 0, "reqReadyDelay must be non-negative")
  require(memRespLatency >= 0, "memRespLatency must be non-negative")

  val io = IO(new DADAOTestMemoryIO(params, maxEntries))

  private val indexBits = math.max(1, log2Ceil(maxEntries))
  private val readyDelayBits =
    math.max(1, log2Ceil(reqReadyDelay + 1))
  private val responseDelayBits =
    math.max(1, log2Ceil(memRespLatency + 1))

  private val entries = RegInit(
    VecInit(
      Seq.fill(maxEntries)(
        0.U.asTypeOf(
          new DADAOTestMemoryEntry(params.addrBits, params.dataBits)
        )
      )
    )
  )

  private val busy = RegInit(false.B)
  private val heldReq = RegInit(
    0.U.asTypeOf(new DADAOMemReq(params.addrBits, params.dataBits))
  )
  private val readyWait = RegInit(0.U(readyDelayBits.W))
  private val responseWait = RegInit(0.U(responseDelayBits.W))

  private val requestCount = RegInit(0.U(32.W))
  private val responseCount = RegInit(0.U(32.W))
  private val writeCount = RegInit(0.U(32.W))
  private val faultCount = RegInit(0.U(32.W))
  private val unmappedCount = RegInit(0.U(32.W))

  private val accessCheck = Module(new DADAOAccessCheck(params))
  accessCheck.io.addr := heldReq.addr
  accessCheck.io.write := heldReq.write
  accessCheck.io.size := heldReq.size
  accessCheck.io.kind := heldReq.kind

  private val alignedAddress =
    Cat(heldReq.addr(params.addrBits - 1, 3), 0.U(3.W))
  private val addrLow = heldReq.addr(2, 0)

  private val hitVec = entries.map { entry =>
    entry.valid && entry.address === alignedAddress
  }
  private val hit = hitVec.reduce(_ || _)
  private val selectedData = Mux1H(hitVec, entries.map(_.data))
  private val selectedWritable = Mux1H(hitVec, entries.map(_.writable))
  private val selectedFault = Mux1H(hitVec, entries.map(_.fault))
  private val selectedFaultCode =
    Mux1H(hitVec, entries.map(_.faultCode))
  private val mergedData = DADAOByteLane.mergeWrite(
    selectedData,
    heldReq.wdata,
    addrLow,
    heldReq.size,
    heldReq.wstrb
  )
  private val responseData = DADAOByteLane.readValue(
    Mux(heldReq.write, mergedData, selectedData),
    addrLow,
    heldReq.size
  )

  private val freeVec = entries.map(entry => !entry.valid)
  private val hasFreeEntry = freeVec.reduce(_ || _)
  private val freeIndexOH = PriorityEncoderOH(freeVec)
  private val writeAllocates =
    heldReq.write &&
      !hit &&
      hasFreeEntry &&
      !accessCheck.io.fault
  private val entryUnmapped = !hit && !writeAllocates
  private val addressUnmapped =
    accessCheck.io.faultCode === DADAOFaultCode.Unmapped.U
  private val responseUnmapped = addressUnmapped || entryUnmapped
  private val readOnlyWrite = heldReq.write && hit && !selectedWritable
  private val responseFault =
    accessCheck.io.fault ||
      entryUnmapped ||
      readOnlyWrite ||
      (hit && selectedFault)
  private val responseFaultCode = Mux(
    accessCheck.io.fault,
    accessCheck.io.faultCode,
    Mux(
      entryUnmapped,
      DADAOFaultCode.Unmapped.U(8.W),
      Mux(
        readOnlyWrite,
        DADAOFaultCode.Illi.U(8.W),
        selectedFaultCode
      )
    )
  )

  private val responseDue = busy && responseWait === 0.U
  private val responseFire = responseDue && io.resp.ready

  io.req.ready :=
    !busy && readyWait >= reqReadyDelay.U

  io.resp.valid := responseDue
  io.resp.bits.rdata := responseData
  io.resp.bits.fault := responseFault
  io.resp.bits.faultCode := responseFaultCode

  io.stats.requestCount := requestCount
  io.stats.responseCount := responseCount
  io.stats.writeCount := writeCount
  io.stats.faultCount := faultCount
  io.stats.unmappedCount := unmappedCount
  io.debugPeek := entries(io.debugPeekIndex)

  when(io.load.valid) {
    entries(io.load.index).valid := true.B
    entries(io.load.index).address := Cat(
      io.load.address(params.addrBits - 1, 3),
      0.U(3.W)
    )
    entries(io.load.index).data := io.load.data
    entries(io.load.index).writable := io.load.writable
    entries(io.load.index).fault := io.load.fault
    entries(io.load.index).faultCode := io.load.faultCode
  }

  when(!busy && !io.req.valid) {
    readyWait := 0.U
  }.elsewhen(!busy && !io.req.ready) {
    readyWait := readyWait + 1.U
  }

  when(io.req.valid && io.req.ready) {
    busy := true.B
    heldReq := io.req.bits
    responseWait := memRespLatency.U
    readyWait := 0.U
    requestCount := requestCount + 1.U
  }

  when(busy && !responseDue) {
    responseWait := responseWait - 1.U
  }

  when(responseFire) {
    busy := false.B
    responseCount := responseCount + 1.U

    when(responseFault) {
      faultCount := faultCount + 1.U
      when(responseUnmapped) {
        unmappedCount := unmappedCount + 1.U
      }
    }.elsewhen(heldReq.write) {
      writeCount := writeCount + 1.U
    }

    when(
      heldReq.write &&
      !responseFault
    ) {
      for (index <- 0 until maxEntries) {
        when(hitVec(index)) {
          entries(index).data := mergedData
        }.elsewhen(writeAllocates && freeIndexOH(index)) {
          entries(index).valid := true.B
          entries(index).address := alignedAddress
          entries(index).data := mergedData
          entries(index).writable := true.B
          entries(index).fault := false.B
          entries(index).faultCode := 0.U
        }
      }
    }
  }
}
