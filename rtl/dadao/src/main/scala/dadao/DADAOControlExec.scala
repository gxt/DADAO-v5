package dadao

import chisel3._
import chisel3.util.{Cat, Fill, Mux1H, MuxLookup}

private[dadao] object DADAOControlOperation {
  val BrN: Int = 1
  val BrNN: Int = 2
  val BrZ: Int = 3
  val BrNZ: Int = 4
  val BrP: Int = 5
  val BrNP: Int = 6
  val BranchEqual: Int = 7
  val BranchNotEqual: Int = 8
  val JumpRelative: Int = 9
  val JumpIndexed: Int = 10
  val CallRelative: Int = 11
  val CallIndexed: Int = 12
  val Ret: Int = 13
}

private[dadao] final case class DADAOControlEntry(
    id: Int,
    operation: Int,
    read0Bank: Int,
    read0Low: Int,
    read1Bank: Int,
    read1Low: Int,
    immLow: Int,
    immWidth: Int
) {
  def isBranch: Boolean =
    operation >= DADAOControlOperation.BrN &&
      operation <= DADAOControlOperation.BranchNotEqual

  def isJump: Boolean =
    operation >= DADAOControlOperation.JumpRelative &&
      operation <= DADAOControlOperation.JumpIndexed

  def isCall: Boolean =
    operation >= DADAOControlOperation.CallRelative &&
      operation <= DADAOControlOperation.CallIndexed

  def isRet: Boolean =
    operation == DADAOControlOperation.Ret
}

private[dadao] object DADAOControlTable {
  private val idIndex =
    DADAODecoderTable.ids.zipWithIndex.toMap

  private def id(name: String): Int =
    idIndex.getOrElse(
      name,
      throw new IllegalArgumentException(s"missing control id: $name")
    )

  val entries: Seq[DADAOControlEntry] = Seq(
    DADAOControlEntry(id("br.n_riii_rd"), DADAOControlOperation.BrN, 0, 18, -1, -1, 0, 18),
    DADAOControlEntry(id("br.nn_riii_rd"), DADAOControlOperation.BrNN, 0, 18, -1, -1, 0, 18),
    DADAOControlEntry(id("br.z_riii_rd"), DADAOControlOperation.BrZ, 0, 18, -1, -1, 0, 18),
    DADAOControlEntry(id("br.nz_riii_rd"), DADAOControlOperation.BrNZ, 0, 18, -1, -1, 0, 18),
    DADAOControlEntry(id("br.p_riii_rd"), DADAOControlOperation.BrP, 0, 18, -1, -1, 0, 18),
    DADAOControlEntry(id("br.np_riii_rd"), DADAOControlOperation.BrNP, 0, 18, -1, -1, 0, 18),
    DADAOControlEntry(id("br.eq_rrii_rd"), DADAOControlOperation.BranchEqual, 0, 18, 0, 12, 0, 12),
    DADAOControlEntry(id("br.ne_rrii_rd"), DADAOControlOperation.BranchNotEqual, 0, 18, 0, 12, 0, 12),
    DADAOControlEntry(id("br.z_riii_rb"), DADAOControlOperation.BrZ, 1, 18, -1, -1, 0, 18),
    DADAOControlEntry(id("br.nz_riii_rb"), DADAOControlOperation.BrNZ, 1, 18, -1, -1, 0, 18),
    DADAOControlEntry(id("jump_iiii_rb"), DADAOControlOperation.JumpRelative, -1, -1, -1, -1, 0, 24),
    DADAOControlEntry(id("jump_rrii_rb"), DADAOControlOperation.JumpIndexed, 1, 18, 0, 12, 0, 12),
    DADAOControlEntry(id("call_iiii_ra"), DADAOControlOperation.CallRelative, -1, -1, -1, -1, 0, 24),
    DADAOControlEntry(id("call_rrii_ra"), DADAOControlOperation.CallIndexed, 1, 18, 0, 12, 0, 12),
    DADAOControlEntry(id("ret_riii_ra"), DADAOControlOperation.Ret, -1, -1, -1, -1, 0, 18)
  )
}

final class DADAOControlExecIO(
    val params: DADAOParams
) extends Bundle {
  val decoded = Input(new DADAODecodedInstruction)
  val currentRb0 = Input(UInt(params.addrBits.W))
  val read0Value = Input(UInt(64.W))
  val read1Value = Input(UInt(64.W))
  val poppedReturnAddress = Input(UInt(48.W))

  val read0Bank = Output(UInt(2.W))
  val read0Addr = Output(UInt(6.W))
  val read1Bank = Output(UInt(2.W))
  val read1Addr = Output(UInt(6.W))

  val isControl = Output(Bool())
  val isBranch = Output(Bool())
  val isJump = Output(Bool())
  val isCall = Output(Bool())
  val isRet = Output(Bool())
  val taken = Output(Bool())
  val target = Output(UInt(params.addrBits.W))
  val nextRb0 = Output(UInt(params.addrBits.W))
  val callReturnAddress = Output(UInt(48.W))
  val retRdWrite = Output(Bool())
  val retRdAddr = Output(UInt(6.W))
  val retRdValue = Output(UInt(64.W))
}

final class DADAOControlExec(
    val params: DADAOParams = DADAOParams()
) extends Module {
  val io = IO(new DADAOControlExecIO(params))
  require(params.addrBits == 64, "control flow requires a 64-bit rb0")

  private val entries = DADAOControlTable.entries
  private val matches = VecInit(
    entries.map(entry => io.decoded.id === entry.id.U(9.W))
  )

  private def selectEntryInt(
      select: DADAOControlEntry => Int
  ): UInt =
    Mux1H(
      matches,
      entries.map { entry =>
        val value = select(entry)
        (if (value >= 0) value else 0).U(2.W)
      }
    )

  private def refAddr(low: Int): UInt =
    if (low < 0) 0.U(6.W)
    else io.decoded.word(low + 5, low)

  private def signExtend(value: UInt, width: Int): UInt =
    if (width == 64) value
    else Cat(Fill(64 - width, value(width - 1)), value)

  private val operation =
    Mux1H(matches, entries.map(_.operation.U(5.W)))
  private val isBranch =
    operation >= DADAOControlOperation.BrN.U &&
      operation <= DADAOControlOperation.BranchNotEqual.U
  private val isJump =
    operation >= DADAOControlOperation.JumpRelative.U &&
      operation <= DADAOControlOperation.JumpIndexed.U
  private val isCall =
    operation >= DADAOControlOperation.CallRelative.U &&
      operation <= DADAOControlOperation.CallIndexed.U
  private val isRet =
    operation === DADAOControlOperation.Ret.U
  private val isIndexedJump =
    operation === DADAOControlOperation.JumpIndexed.U ||
      operation === DADAOControlOperation.CallIndexed.U

  io.read0Bank := selectEntryInt(_.read0Bank)
  io.read0Addr := Mux1H(
    matches,
    entries.map(entry => refAddr(entry.read0Low))
  )
  io.read1Bank := selectEntryInt(_.read1Bank)
  io.read1Addr := Mux1H(
    matches,
    entries.map(entry => refAddr(entry.read1Low))
  )

  private val immediate =
    Mux1H(
      matches,
      entries.map { entry =>
        signExtend(
          io.decoded.word(entry.immLow + entry.immWidth - 1, entry.immLow),
          entry.immWidth
        )
      }
    )
  private val offset64 = immediate << 2
  private val relativeTarget = io.currentRb0 + offset64
  private val indexedTarget =
    io.read0Value + io.read1Value + offset64
  private val returnTarget =
    Cat(0.U(16.W), io.poppedReturnAddress)
  private val target =
    Mux(
      isRet,
      returnTarget,
      Mux(isIndexedJump, indexedTarget, relativeTarget)
    )

  private val taken = MuxLookup(operation, false.B)(
    Seq(
      DADAOControlOperation.BrN.U -> io.read0Value(63),
      DADAOControlOperation.BrNN.U -> !io.read0Value(63),
      DADAOControlOperation.BrZ.U -> (io.read0Value === 0.U),
      DADAOControlOperation.BrNZ.U -> (io.read0Value =/= 0.U),
      DADAOControlOperation.BrP.U ->
        (!io.read0Value(63) && io.read0Value =/= 0.U),
      DADAOControlOperation.BrNP.U ->
        (io.read0Value(63) || io.read0Value === 0.U),
      DADAOControlOperation.BranchEqual.U ->
        (io.read0Value === io.read1Value),
      DADAOControlOperation.BranchNotEqual.U ->
        (io.read0Value =/= io.read1Value),
      DADAOControlOperation.JumpRelative.U -> true.B,
      DADAOControlOperation.JumpIndexed.U -> true.B,
      DADAOControlOperation.CallRelative.U -> true.B,
      DADAOControlOperation.CallIndexed.U -> true.B,
      DADAOControlOperation.Ret.U -> true.B
    )
  )

  io.isControl := isBranch || isJump || isCall || isRet
  io.isBranch := isBranch
  io.isJump := isJump
  io.isCall := isCall
  io.isRet := isRet
  io.taken := taken
  io.target := target
  io.nextRb0 := Mux(taken, target, io.currentRb0 + 4.U)
  io.callReturnAddress := (io.currentRb0 + 4.U)(47, 0)
  io.retRdWrite :=
    isRet && io.decoded.word(23, 18) =/= 0.U
  io.retRdAddr := io.decoded.word(23, 18)
  io.retRdValue :=
    signExtend(io.decoded.word(17, 0), 18)
}
