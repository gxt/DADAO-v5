package dadao

import chisel3._
import chisel3.util.{Cat, Fill, Mux1H, MuxLookup}

private final case class DADAOBlockMemMeta(
    id: Int,
    width: Int,
    signed: Boolean,
    store: Boolean,
    bank: Int
)

private object DADAOBlockMemTable {
  private def widthFor(id: String): Int =
    if (
      id.startsWith("ldm.ub") ||
      id.startsWith("ldm.sb") ||
      id.startsWith("stm.b")
    ) 8
    else if (
      id.startsWith("ldm.uw") ||
      id.startsWith("ldm.sw") ||
      id.startsWith("stm.w")
    ) 16
    else if (
      id.startsWith("ldm.ut") ||
      id.startsWith("ldm.st") ||
      id.startsWith("stm.t")
    ) 32
    else if (id.startsWith("ldm.o") || id.startsWith("stm.o")) 64
    else {
      throw new IllegalArgumentException(
        s"unsupported block memory id: $id"
      )
    }

  private def signedFor(id: String): Boolean =
    id.startsWith("ldm.sb") ||
      id.startsWith("ldm.sw") ||
      id.startsWith("ldm.st")

  private def bankFor(id: String): Int =
    if (id.endsWith("_rb")) DADAORegBank.Rb
    else if (id.endsWith("_ra")) DADAORegBank.Ra
    else DADAORegBank.Rd

  val entries: Seq[DADAOBlockMemMeta] =
    DADAODecoderTable.ids.zipWithIndex.collect {
      case (id, index)
          if DADAODecoderTable.entries(index).scope == DADAOScope.M1 &&
            (
              id.startsWith("ldm.") ||
                id.startsWith("stm.")
            ) =>
        DADAOBlockMemMeta(
          index,
          widthFor(id),
          signedFor(id),
          id.startsWith("stm."),
          bankFor(id)
        )
    }

  require(entries.size == 15, s"expected 15 M1 block memory operations")
  require(
    entries.map(_.id).distinct.size == entries.size,
    "duplicate block memory ids"
  )
}

final class DADAOBlockMemExecIO(val params: DADAOParams) extends Bundle {
  val decoded = Input(new DADAODecodedInstruction)
  val baseValue = Input(UInt(64.W))
  val offsetValue = Input(UInt(64.W))
  val address = Input(UInt(params.addrBits.W))
  val sourceValue = Input(UInt(64.W))
  val responseValue = Input(UInt(64.W))

  val isBlock = Output(Bool())
  val isLoad = Output(Bool())
  val isStore = Output(Bool())
  val firstAddress = Output(UInt(params.addrBits.W))
  val requestSize = Output(UInt(3.W))
  val startRegAddr = Output(UInt(6.W))
  val baseRegAddr = Output(UInt(6.W))
  val offsetRegAddr = Output(UInt(6.W))
  val targetBank = Output(UInt(2.W))
  val count = Output(UInt(6.W))
  val requestWdata = Output(UInt(64.W))
  val requestWstrb = Output(UInt(8.W))
  val loadValue = Output(UInt(64.W))
}

final class DADAOBlockMemExec(
    val params: DADAOParams = DADAOParams()
) extends Module {
  val io = IO(new DADAOBlockMemExecIO(params))

  private val entries = DADAOBlockMemTable.entries
  private val matches = VecInit(
    entries.map(entry => io.decoded.id === entry.id.U(9.W))
  )
  private val hit = matches.asUInt.orR

  private def select(selector: DADAOBlockMemMeta => Int): UInt =
    Mux1H(matches, entries.map(entry => selector(entry).U))

  private val width = select(_.width)
  private val signed = Mux1H(matches, entries.map(_.signed.B))
  private val store = Mux1H(matches, entries.map(_.store.B))
  private val targetBank = select(_.bank)
  private val startRegAddr = io.decoded.word(23, 18)
  private val baseRegAddr = io.decoded.word(17, 12)
  private val offsetRegAddr = io.decoded.word(11, 6)
  private val count = io.decoded.word(5, 0)
  private val requestSize = MuxLookup(width, DADAOMemSize.Byte.U)(
    Seq(
      8.U -> DADAOMemSize.Byte.U,
      16.U -> DADAOMemSize.Wyde.U,
      32.U -> DADAOMemSize.Tetra.U,
      64.U -> DADAOMemSize.Octa.U
    )
  )
  private val requestWdata = MuxLookup(width, io.sourceValue)(
    Seq(
      8.U -> Cat(0.U(56.W), io.sourceValue(7, 0)),
      16.U -> Cat(0.U(48.W), io.sourceValue(15, 0)),
      32.U -> Cat(0.U(32.W), io.sourceValue(31, 0)),
      64.U -> io.sourceValue
    )
  )
  private def signExtend(value: UInt, width: Int): UInt =
    if (width == 64) value
    else Cat(Fill(64 - width, value(width - 1)), value(width - 1, 0))

  private def zeroExtend(value: UInt, width: Int): UInt =
    if (width == 64) value
    else Cat(0.U((64 - width).W), value(width - 1, 0))

  private val loadValue = MuxLookup(width, io.responseValue)(
    Seq(
      8.U -> Mux(
        signed,
        signExtend(io.responseValue, 8),
        zeroExtend(io.responseValue, 8)
      ),
      16.U -> Mux(
        signed,
        signExtend(io.responseValue, 16),
        zeroExtend(io.responseValue, 16)
      ),
      32.U -> Mux(
        signed,
        signExtend(io.responseValue, 32),
        zeroExtend(io.responseValue, 32)
      ),
      64.U -> io.responseValue
    )
  )

  io.isBlock := hit
  io.isLoad := hit && !store
  io.isStore := hit && store
  io.firstAddress := io.baseValue + io.offsetValue
  io.requestSize := requestSize
  io.startRegAddr := startRegAddr
  io.baseRegAddr := baseRegAddr
  io.offsetRegAddr := offsetRegAddr
  io.targetBank := targetBank
  io.count := count
  io.requestWdata := requestWdata
  io.requestWstrb := DADAOByteLane.laneMask(
    io.address(2, 0),
    requestSize
  )
  io.loadValue := loadValue
}
