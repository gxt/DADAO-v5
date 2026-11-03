package dadao

import chisel3._
import chisel3.util.{Cat, Fill, Mux1H, MuxLookup}

private final case class DADAOStoreMeta(
    id: Int,
    width: Int,
    sourceBank: Int
)

private object DADAOStoreTable {
  private def widthFor(id: String): Int =
    if (id.startsWith("st.b")) 8
    else if (id.startsWith("st.w")) 16
    else if (id.startsWith("st.t")) 32
    else if (id.startsWith("st.o")) 64
    else {
      throw new IllegalArgumentException(s"unsupported store id: $id")
    }

  private def sourceBankFor(id: String): Int =
    if (id.endsWith("_rb")) DADAORegBank.Rb
    else if (id.endsWith("_ra")) DADAORegBank.Ra
    else DADAORegBank.Rd

  val entries: Seq[DADAOStoreMeta] =
    DADAODecoderTable.ids.zipWithIndex.collect {
      case (id, index)
          if DADAODecoderTable.entries(index).scope == DADAOScope.M1 &&
            id.startsWith("st.") &&
            !id.startsWith("stm.") =>
        DADAOStoreMeta(
          index,
          widthFor(id),
          sourceBankFor(id)
        )
    }

  require(entries.size == 6, s"expected 6 single stores, got ${entries.size}")
  require(
    entries.map(_.id).distinct.size == entries.size,
    "duplicate single-store ids"
  )
}

final class DADAOStoreExecIO(val params: DADAOParams) extends Bundle {
  val decoded = Input(new DADAODecodedInstruction)
  val baseValue = Input(UInt(64.W))
  val sourceValue = Input(UInt(64.W))

  val isStore = Output(Bool())
  val baseRegAddr = Output(UInt(6.W))
  val sourceBank = Output(UInt(2.W))
  val sourceRegAddr = Output(UInt(6.W))
  val requestAddr = Output(UInt(params.addrBits.W))
  val requestSize = Output(UInt(3.W))
  val requestWdata = Output(UInt(params.dataBits.W))
  val requestWstrb = Output(UInt((params.dataBits / 8).W))
}

final class DADAOStoreExec(
    val params: DADAOParams = DADAOParams()
) extends Module {
  val io = IO(new DADAOStoreExecIO(params))

  private val entries = DADAOStoreTable.entries
  private val matches = VecInit(
    entries.map(entry => io.decoded.id === entry.id.U(9.W))
  )
  private val hit = matches.asUInt.orR

  private def select(selector: DADAOStoreMeta => Int): UInt =
    Mux1H(matches, entries.map(entry => selector(entry).U))

  private val width = select(_.width)
  private val sourceBank = select(_.sourceBank)
  private val sourceRegAddr = io.decoded.word(23, 18)
  private val baseRegAddr = io.decoded.word(17, 12)
  private val immediateRaw = io.decoded.word(11, 0)
  private val immediate = Cat(
    Fill(52, immediateRaw(11)),
    immediateRaw
  )
  private val effectiveAddr = io.baseValue + immediate

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

  io.isStore := hit
  io.baseRegAddr := baseRegAddr
  io.sourceBank := sourceBank
  io.sourceRegAddr := sourceRegAddr
  io.requestAddr := effectiveAddr
  io.requestSize := requestSize
  io.requestWdata := requestWdata
  io.requestWstrb := DADAOByteLane.laneMask(
    effectiveAddr(2, 0),
    requestSize
  )
}
