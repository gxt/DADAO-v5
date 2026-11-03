package dadao

import chisel3._
import chisel3.util.{Cat, Fill, Mux1H, MuxLookup}

private final case class DADAOLoadMeta(
    id: Int,
    width: Int,
    signed: Boolean,
    bank: Int
)

private object DADAOLoadTable {
  private def widthAndSigned(id: String): (Int, Boolean) =
    if (id.startsWith("ld.sb")) (8, true)
    else if (id.startsWith("ld.ub")) (8, false)
    else if (id.startsWith("ld.sw")) (16, true)
    else if (id.startsWith("ld.uw")) (16, false)
    else if (id.startsWith("ld.st")) (32, true)
    else if (id.startsWith("ld.ut")) (32, false)
    else if (id.startsWith("ld.o")) (64, false)
    else {
      throw new IllegalArgumentException(s"unsupported load id: $id")
    }

  private def bankFor(id: String): Int =
    if (id.endsWith("_rb")) DADAORegBank.Rb
    else if (id.endsWith("_ra")) DADAORegBank.Ra
    else DADAORegBank.Rd

  val entries: Seq[DADAOLoadMeta] =
    DADAODecoderTable.ids.zipWithIndex.collect {
      case (id, index)
          if DADAODecoderTable.entries(index).scope == DADAOScope.M1 &&
            id.startsWith("ld.") &&
            !id.startsWith("ldm.") =>
        val (width, signed) = widthAndSigned(id)
        DADAOLoadMeta(index, width, signed, bankFor(id))
    }

  val memoryIds: Set[Int] =
    DADAODecoderTable.ids.zipWithIndex.collect {
      case (id, index)
          if DADAODecoderTable.entries(index).scope == DADAOScope.M1 &&
            (
              id.startsWith("ld.") ||
                id.startsWith("st.") ||
                id.startsWith("ldm.") ||
                id.startsWith("stm.")
            ) =>
        index
    }.toSet

  require(entries.size == 9, s"expected 9 single loads, got ${entries.size}")
  require(
    entries.map(_.id).distinct.size == entries.size,
    "duplicate single-load ids"
  )
  require(memoryIds.size == 30, s"expected 30 memory ids, got ${memoryIds.size}")
}

final class DADAOLoadExecIO(val params: DADAOParams) extends Bundle {
  val decoded = Input(new DADAODecodedInstruction)
  val baseValue = Input(UInt(64.W))
  val responseData = Input(UInt(64.W))
  val responseValid = Input(Bool())
  val responseFault = Input(Bool())

  val isLoad = Output(Bool())
  val isMemory = Output(Bool())
  val baseRegAddr = Output(UInt(6.W))
  val requestAddr = Output(UInt(params.addrBits.W))
  val requestSize = Output(UInt(3.W))

  val write = Output(new DADAOTestRegWrite)
}

final class DADAOLoadExec(
    val params: DADAOParams = DADAOParams()
) extends Module {
  val io = IO(new DADAOLoadExecIO(params))

  private val entries = DADAOLoadTable.entries
  private val matches = VecInit(
    entries.map(entry => io.decoded.id === entry.id.U(9.W))
  )
  private val hit = matches.asUInt.orR

  private def select(selector: DADAOLoadMeta => Int): UInt =
    Mux1H(matches, entries.map(entry => selector(entry).U))

  private val width = select(_.width)
  private val bank = select(_.bank)
  private val signed = Mux1H(matches, entries.map(_.signed.B))
  private val destAddr = io.decoded.word(23, 18)
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
  private val rawValue = io.responseData
  private def signExtend(value: UInt, width: Int): UInt =
    if (width == 64) value
    else Cat(Fill(64 - width, value(width - 1)), value(width - 1, 0))

  private def zeroExtend(value: UInt, width: Int): UInt =
    if (width == 64) value
    else Cat(0.U((64 - width).W), value(width - 1, 0))

  private val extendedValue = MuxLookup(width, rawValue)(
    Seq(
      8.U -> Mux(
        signed,
        signExtend(rawValue, 8),
        zeroExtend(rawValue, 8)
      ),
      16.U -> Mux(
        signed,
        signExtend(rawValue, 16),
        zeroExtend(rawValue, 16)
      ),
      32.U -> Mux(
        signed,
        signExtend(rawValue, 32),
        zeroExtend(rawValue, 32)
      ),
      64.U -> rawValue
    )
  )

  io.isLoad := hit
  io.isMemory := DADAOLoadTable.memoryIds
    .map(id => io.decoded.id === id.U(9.W))
    .reduce(_ || _)
  io.baseRegAddr := baseRegAddr
  io.requestAddr := effectiveAddr
  io.requestSize := requestSize
  io.write.valid := hit && io.responseValid && !io.responseFault
  io.write.bank := bank
  io.write.addr := destAddr
  io.write.data := extendedValue
}
