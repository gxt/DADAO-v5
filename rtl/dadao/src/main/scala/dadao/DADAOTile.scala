package dadao

import chisel3._
import freechips.rocketchip.diplomacy._
import freechips.rocketchip.interrupts._
import freechips.rocketchip.prci.{ClockCrossingType, ClockSinkParameters, SynchronousCrossing}
import freechips.rocketchip.rocket.{BTBParams, DCacheParams, ICacheParams, MulDivParams}
import freechips.rocketchip.subsystem._
import freechips.rocketchip.tile._
import freechips.rocketchip.tilelink._
import org.chipsalliance.cde.config.Parameters

final case class DADAOCoreParams(
    bootFreqHz: BigInt = BigInt(1000000000),
    useDebug: Boolean = false,
    useAtomics: Boolean = false,
    useCompressed: Boolean = false,
    nLocalInterrupts: Int = 0,
    nPMPs: Int = 0,
    nBreakpoints: Int = 0,
    nPerfCounters: Int = 0,
    xLen: Int = 64,
    pgLevels: Int = 3
) extends CoreParams {
  val useVM: Boolean = false
  val useHypervisor: Boolean = false
  val useUser: Boolean = false
  val useSupervisor: Boolean = false
  val useAtomicsOnlyForIO: Boolean = false
  override val useVector: Boolean = false
  val useRVE: Boolean = false
  val useConditionalZero: Boolean = false
  val useZba: Boolean = false
  val useZbb: Boolean = false
  val useZbs: Boolean = false
  val mulDiv: Option[MulDivParams] = None
  val fpu: Option[FPUParams] = None
  val fetchWidth: Int = 1
  val decodeWidth: Int = 1
  val retireWidth: Int = 1
  val instBits: Int = 32
  val useNMI: Boolean = false
  val pmpGranularity: Int = 4
  val useBPWatch: Boolean = false
  val mcontextWidth: Int = 0
  val scontextWidth: Int = 0
  val haveBasicCounters: Boolean = false
  val haveFSDirty: Boolean = false
  val misaWritable: Boolean = false
  val haveCFlush: Boolean = false
  val nL2TLBEntries: Int = 0
  val nL2TLBWays: Int = 0
  val nPTECacheEntries: Int = 0
  val mtvecInit: Option[BigInt] = None
  val mtvecWritable: Boolean = false
  val traceHasWdata: Boolean = false
  val lrscCycles: Int = 1
}

final case class DADAOTileParams(
    tileId: Int = 0,
    val core: DADAOCoreParams = DADAOCoreParams(),
    dadao: DADAOParams = DADAOParams()
) extends InstantiableTileParams[DADAOTile] {
  val baseName: String = "dadao"
  val uniqueName: String = s"${baseName}_$tileId"
  val icache: Option[ICacheParams] = None
  val dcache: Option[DCacheParams] = None
  val btb: Option[BTBParams] = None
  val blockerCtrlAddr: Option[BigInt] = None
  val clockSinkParams: ClockSinkParameters = ClockSinkParameters()

  def instantiate(
      crossing: HierarchicalElementCrossingParamsLike,
      lookup: LookupByHartIdImpl
  )(implicit p: Parameters): DADAOTile =
    new DADAOTile(this, crossing, lookup)
}

final case class DADAOTileAttachParams(
    tileParams: DADAOTileParams = DADAOTileParams(),
    crossingParams: RocketCrossingParams = RocketCrossingParams()
) extends CanAttachTile {
  type TileType = DADAOTile
  val lookup: LookupByHartIdImpl = PriorityMuxHartIdFromSeq(Seq(tileParams))
}

final class DADAOTile(
    val dadaoParams: DADAOTileParams,
    crossing: ClockCrossingType,
    lookup: LookupByHartIdImpl,
    q: Parameters
) extends BaseTile(dadaoParams, crossing, lookup, q) {

  def this(
      params: DADAOTileParams,
      crossing: HierarchicalElementCrossingParamsLike,
      lookup: LookupByHartIdImpl
  )(implicit p: Parameters) =
    this(params, crossing.crossingType, lookup, p)

  val intInwardNode: IntInwardNode = IntIdentityNode()
  val intOutwardNode: Option[IntOutwardNode] = None
  val haltNode: IntOutwardNode = IntSourceNode(IntSourcePortSimple())
  val ceaseNode: IntOutwardNode = IntSourceNode(IntSourcePortSimple())
  val wfiNode: IntOutwardNode = IntSourceNode(IntSourcePortSimple())
  val masterNode = visibilityNode
  val slaveNode: TLInwardNode = TLIdentityNode()

  override protected def visiblePhysAddrBits: Int =
    dadaoParams.dadao.addrBits

  override lazy val module: DADAOTileModuleImp =
    new DADAOTileModuleImp(this)
}

final class DADAOTileModuleImp(outer: DADAOTile) extends BaseTileModuleImp(outer) {
  val io = IO(new Bundle {
    val pc = Output(UInt(outer.dadaoParams.dadao.addrBits.W))
  })

  val cpu = Module(new DADAOCpuTop(outer.dadaoParams.dadao))
  io.pc := cpu.io.pc
}
