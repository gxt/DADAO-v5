package dadao

import chisel3._
import chisel3.util.{Cat, Fill, MuxLookup}

final class DADAOALUIO extends Bundle {
  val operation = Input(UInt(5.W))
  val widthCode = Input(UInt(2.W))
  val signed = Input(Bool())
  val dualResult = Input(Bool())

  val operandA = Input(UInt(64.W))
  val operandB = Input(UInt(64.W))
  val operandC = Input(UInt(64.W))
  val operandD = Input(UInt(64.W))
  val auxIndex = Input(UInt(6.W))

  val resultLo = Output(UInt(64.W))
  val resultHi = Output(UInt(64.W))
  val primaryCommit = Output(Bool())
  val validOp = Output(Bool())
}

final class DADAOALU extends Module {
  val io = IO(new DADAOALUIO)

  private val resultLo = WireDefault(0.U(64.W))
  private val resultHi = WireDefault(0.U(64.W))
  private val primaryCommit = WireDefault(false.B)
  private val validOp = WireDefault(false.B)

  private def zeroExtend(value: UInt, width: Int): UInt =
    if (width == 64) value
    else Cat(0.U((64 - width).W), value)

  private def signExtend(value: UInt, width: Int): UInt =
    if (width == 64) value
    else Cat(Fill(64 - width, value(width - 1)), value)

  private def extendValue(value: UInt, width: Int): UInt =
    Mux(io.signed, signExtend(value, width), zeroExtend(value, width))

  private def selectWidth(
      w8: UInt,
      w16: UInt,
      w32: UInt,
      w64: UInt
  ): UInt =
    Mux(
      io.widthCode === DADAOExecWidth.W8.U,
      w8,
      Mux(
        io.widthCode === DADAOExecWidth.W16.U,
        w16,
        Mux(
          io.widthCode === DADAOExecWidth.W32.U,
          w32,
          w64
        )
      )
    )

  private def addNarrow(width: Int): UInt = {
    val lhs = io.operandA(width - 1, 0)
    val rhs = io.operandB(width - 1, 0)
    val sum =
      Cat(0.U(1.W), lhs) + Cat(0.U(1.W), rhs)
    extendValue(sum(width - 1, 0), width)
  }

  private def subNarrow(width: Int): UInt = {
    val lhs = io.operandA(width - 1, 0)
    val rhs = io.operandB(width - 1, 0)
    val difference =
      Cat(0.U(1.W), lhs) - Cat(0.U(1.W), rhs)
    extendValue(difference(width - 1, 0), width)
  }

  private def compareNarrow(width: Int): UInt = {
    val lhs = io.operandA(width - 1, 0)
    val rhs = io.operandB(width - 1, 0)
    val less =
      Mux(
        io.signed,
        lhs.asSInt < rhs.asSInt,
        lhs < rhs
      )
    val equal = lhs === rhs
    Mux(
      less,
      BigInt("ffffffffffffffff", 16).U,
      Mux(equal, 0.U, 1.U)
    )
  }

  private def shiftLeftNarrow(width: Int): UInt = {
    val source = io.operandA(width - 1, 0)
    val shifted = source << io.auxIndex
    extendValue(shifted(width - 1, 0), width)
  }

  private def shiftRightNarrow(width: Int): UInt = {
    val source = io.operandA(width - 1, 0)
    val shifted = Mux(
      io.signed,
      (source.asSInt >> io.auxIndex).asUInt,
      source >> io.auxIndex
    )
    extendValue(shifted(width - 1, 0), width)
  }

  private def twosComplement(value: UInt, width: Int): UInt = {
    val inverted = ~value
    (inverted + 1.U(width.W))(width - 1, 0)
  }

  private def multiplyNarrow(width: Int): UInt = {
    val lhs = io.operandA(width - 1, 0)
    val rhs = io.operandB(width - 1, 0)
    val product = lhs * rhs
    extendValue(product(width - 1, 0), width)
  }

  private def unsignedDivideNarrow(width: Int): UInt = {
    val lhs = io.operandA(width - 1, 0)
    val rhs = io.operandB(width - 1, 0)
    val zero = rhs === 0.U(width.W)
    val safeRhs = Mux(zero, 1.U(width.W), rhs)
    val quotient = lhs / safeRhs
    val result = Mux(zero, Fill(width, 1.U), quotient)
    extendValue(result, width)
  }

  private def unsignedRemainderNarrow(width: Int): UInt = {
    val lhs = io.operandA(width - 1, 0)
    val rhs = io.operandB(width - 1, 0)
    val zero = rhs === 0.U(width.W)
    val safeRhs = Mux(zero, 1.U(width.W), rhs)
    val remainder = lhs % safeRhs
    val result = Mux(zero, lhs, remainder)
    extendValue(result, width)
  }

  private def signedDivideNarrow(width: Int): UInt = {
    val lhs = io.operandA(width - 1, 0)
    val rhs = io.operandB(width - 1, 0)
    val lhsSign = lhs(width - 1)
    val rhsSign = rhs(width - 1)
    val zero = rhs === 0.U(width.W)
    val lhsMagnitude =
      Mux(lhsSign, twosComplement(lhs, width), lhs)
    val rhsMagnitude =
      Mux(rhsSign, twosComplement(rhs, width), rhs)
    val safeRhs =
      Mux(zero, 1.U(width.W), rhsMagnitude)
    val quotientMagnitude = lhsMagnitude / safeRhs
    val signedQuotient =
      Mux(
        lhsSign ^ rhsSign,
        twosComplement(quotientMagnitude, width),
        quotientMagnitude
      )
    val minSigned =
      (BigInt(1) << (width - 1)).U(width.W)
    val negativeOne = Fill(width, 1.U)
    val overflow = lhs === minSigned && rhs === negativeOne
    val result = Mux(
      zero,
      Fill(width, 1.U),
      Mux(overflow, minSigned, signedQuotient)
    )
    extendValue(result, width)
  }

  private def signedRemainderNarrow(width: Int): UInt = {
    val lhs = io.operandA(width - 1, 0)
    val rhs = io.operandB(width - 1, 0)
    val lhsSign = lhs(width - 1)
    val rhsSign = rhs(width - 1)
    val zero = rhs === 0.U(width.W)
    val lhsMagnitude =
      Mux(lhsSign, twosComplement(lhs, width), lhs)
    val rhsMagnitude =
      Mux(rhsSign, twosComplement(rhs, width), rhs)
    val safeRhs =
      Mux(zero, 1.U(width.W), rhsMagnitude)
    val remainderMagnitude = lhsMagnitude % safeRhs
    val signedRemainder =
      Mux(
        lhsSign,
        twosComplement(remainderMagnitude, width),
        remainderMagnitude
      )
    val minSigned =
      (BigInt(1) << (width - 1)).U(width.W)
    val negativeOne = Fill(width, 1.U)
    val overflow = lhs === minSigned && rhs === negativeOne
    val result = Mux(
      zero,
      lhs,
      Mux(overflow, 0.U(width.W), signedRemainder)
    )
    extendValue(result, width)
  }

  private def signExtended128(value: UInt): SInt =
    Cat(Fill(64, value(63)), value).asSInt

  private val unsignedAdd =
    Cat(0.U(1.W), io.operandA) +
      Cat(0.U(1.W), io.operandB)
  private val unsignedSubBorrow = io.operandA < io.operandB

  private val signedLhs128 = signExtended128(io.operandA)
  private val signedRhs128 = signExtended128(io.operandB)
  private val signedAdd =
    signedLhs128 + signedRhs128
  private val signedSub =
    signedLhs128 - signedRhs128

  private val unsignedProduct = io.operandA * io.operandB
  private val signedProduct =
    (io.operandA.asSInt * io.operandB.asSInt).asUInt

  private val addResult = selectWidth(
    addNarrow(8),
    addNarrow(16),
    addNarrow(32),
    unsignedAdd(63, 0)
  )
  private val subResult = selectWidth(
    subNarrow(8),
    subNarrow(16),
    subNarrow(32),
    Cat(0.U(1.W), io.operandA) -
      Cat(0.U(1.W), io.operandB)
  )

  private val cmpResult = selectWidth(
    compareNarrow(8),
    compareNarrow(16),
    compareNarrow(32),
    {
      val less = Mux(
        io.signed,
        io.operandA.asSInt < io.operandB.asSInt,
        io.operandA < io.operandB
      )
      val equal = io.operandA === io.operandB
      Mux(
        less,
        BigInt("ffffffffffffffff", 16).U,
        Mux(equal, 0.U, 1.U)
      )
    }
  )

  private val mulResult = selectWidth(
    multiplyNarrow(8),
    multiplyNarrow(16),
    multiplyNarrow(32),
    Mux(
      io.signed,
      signedProduct(63, 0),
      unsignedProduct(63, 0)
    )
  )
  private val mulHigh = Mux(
    io.signed,
    signedProduct(127, 64),
    unsignedProduct(127, 64)
  )

  private val divResult = Mux(
    io.signed,
    selectWidth(
      signedDivideNarrow(8),
      signedDivideNarrow(16),
      signedDivideNarrow(32),
      signedDivideNarrow(64)
    ),
    selectWidth(
      unsignedDivideNarrow(8),
      unsignedDivideNarrow(16),
      unsignedDivideNarrow(32),
      unsignedDivideNarrow(64)
    )
  )
  private val remResult = Mux(
    io.signed,
    selectWidth(
      signedRemainderNarrow(8),
      signedRemainderNarrow(16),
      signedRemainderNarrow(32),
      signedRemainderNarrow(64)
    ),
    selectWidth(
      unsignedRemainderNarrow(8),
      unsignedRemainderNarrow(16),
      unsignedRemainderNarrow(32),
      unsignedRemainderNarrow(64)
    )
  )

  private val shiftLeftResult = selectWidth(
    shiftLeftNarrow(8),
    shiftLeftNarrow(16),
    shiftLeftNarrow(32),
    {
      val shifted = io.operandA << io.auxIndex
      shifted(63, 0)
    }
  )
  private val shiftRightResult = selectWidth(
    shiftRightNarrow(8),
    shiftRightNarrow(16),
    shiftRightNarrow(32),
    Mux(
      io.signed,
      (io.operandA.asSInt >> io.auxIndex).asUInt,
      io.operandA >> io.auxIndex
    )
  )

  private val extMasks = Seq.tabulate(64) { index =>
    index.U -> (((BigInt(1) << (index + 1)) - 1).U(64.W))
  }
  private val extMask = MuxLookup(
    io.auxIndex,
    0.U(64.W)
  )(extMasks)
  private val extSign = MuxLookup(
    io.auxIndex,
    false.B
  )(
    Seq.tabulate(64) { index =>
      index.U -> io.operandA(index)
    }
  )
  private val extLow = io.operandA & extMask
  private val extResult = Mux(
    io.signed && extSign,
    extLow | ~extMask,
    extLow
  )

  private val csNegative = io.operandA(63)
  private val csZero = io.operandA === 0.U
  private val csPositive = !csNegative && !csZero
  private val csEqual = io.operandA === io.operandB

  private val wydeShift = io.auxIndex << 4
  private val wydeMask = MuxLookup(
    io.auxIndex,
    0.U(64.W)
  )(
    Seq(
      0.U -> BigInt("000000000000ffff", 16).U(64.W),
      1.U -> BigInt("00000000ffff0000", 16).U(64.W),
      2.U -> BigInt("0000ffff00000000", 16).U(64.W),
      3.U -> BigInt("ffff000000000000", 16).U(64.W)
    )
  )
  private val wydeReplacement =
    (
      Cat(0.U(48.W), io.operandB(15, 0)) << wydeShift
    )(63, 0) & wydeMask

  when(io.operation === DADAOExecOperation.Add.U) {
    resultLo := addResult
    resultHi := Mux(
      io.dualResult &&
        io.widthCode === DADAOExecWidth.W64.U,
      Mux(io.signed, signedAdd(127, 64).asUInt, Cat(0.U(63.W), unsignedAdd(64))),
      0.U
    )
    primaryCommit := true.B
    validOp := true.B
  }.elsewhen(io.operation === DADAOExecOperation.Sub.U) {
    resultLo := subResult
    resultHi := Mux(
      io.dualResult &&
        io.widthCode === DADAOExecWidth.W64.U,
      Mux(
        io.signed,
        signedSub(127, 64).asUInt,
        Mux(unsignedSubBorrow, 1.U, 0.U)
      ),
      0.U
    )
    primaryCommit := true.B
    validOp := true.B
  }.elsewhen(io.operation === DADAOExecOperation.Cmp.U) {
    resultLo := cmpResult
    primaryCommit := true.B
    validOp := true.B
  }.elsewhen(io.operation === DADAOExecOperation.Mul.U) {
    resultLo := mulResult
    resultHi := Mux(
      io.dualResult &&
        io.widthCode === DADAOExecWidth.W64.U,
      mulHigh,
      0.U
    )
    primaryCommit := true.B
    validOp := true.B
  }.elsewhen(io.operation === DADAOExecOperation.Div.U) {
    resultLo := divResult
    primaryCommit := true.B
    validOp := true.B
  }.elsewhen(io.operation === DADAOExecOperation.Rem.U) {
    resultLo := remResult
    primaryCommit := true.B
    validOp := true.B
  }.elsewhen(io.operation === DADAOExecOperation.And.U) {
    resultLo := io.operandA & io.operandB
    primaryCommit := true.B
    validOp := true.B
  }.elsewhen(io.operation === DADAOExecOperation.Or.U) {
    resultLo := io.operandA | io.operandB
    primaryCommit := true.B
    validOp := true.B
  }.elsewhen(io.operation === DADAOExecOperation.Xor.U) {
    resultLo := io.operandA ^ io.operandB
    primaryCommit := true.B
    validOp := true.B
  }.elsewhen(io.operation === DADAOExecOperation.Xnor.U) {
    resultLo := ~(io.operandA ^ io.operandB)
    primaryCommit := true.B
    validOp := true.B
  }.elsewhen(io.operation === DADAOExecOperation.Shl.U) {
    resultLo := shiftLeftResult
    primaryCommit := true.B
    validOp := true.B
  }.elsewhen(io.operation === DADAOExecOperation.Shr.U) {
    resultLo := shiftRightResult
    primaryCommit := true.B
    validOp := true.B
  }.elsewhen(io.operation === DADAOExecOperation.Ext.U) {
    resultLo := extResult
    primaryCommit := true.B
    validOp := true.B
  }.elsewhen(io.operation === DADAOExecOperation.SetOw.U) {
    resultLo := ~wydeMask | wydeReplacement
    primaryCommit := true.B
    validOp := true.B
  }.elsewhen(io.operation === DADAOExecOperation.SetZeroWyde.U) {
    resultLo := wydeReplacement
    primaryCommit := true.B
    validOp := true.B
  }.elsewhen(io.operation === DADAOExecOperation.OrW.U) {
    resultLo := io.operandA | wydeReplacement
    primaryCommit := true.B
    validOp := true.B
  }.elsewhen(io.operation === DADAOExecOperation.AndnW.U) {
    resultLo := io.operandA & ~wydeReplacement
    primaryCommit := true.B
    validOp := true.B
  }.elsewhen(io.operation === DADAOExecOperation.CsN.U) {
    resultLo := Mux(csNegative, io.operandC, io.operandD)
    primaryCommit := true.B
    validOp := true.B
  }.elsewhen(io.operation === DADAOExecOperation.CsZ.U) {
    resultLo := Mux(csZero, io.operandC, io.operandD)
    primaryCommit := true.B
    validOp := true.B
  }.elsewhen(io.operation === DADAOExecOperation.CsP.U) {
    resultLo := Mux(csPositive, io.operandC, io.operandD)
    primaryCommit := true.B
    validOp := true.B
  }.elsewhen(io.operation === DADAOExecOperation.CsEq.U) {
    resultLo := io.operandD
    primaryCommit := csEqual
    validOp := true.B
  }.elsewhen(io.operation === DADAOExecOperation.CsNe.U) {
    resultLo := io.operandD
    primaryCommit := !csEqual
    validOp := true.B
  }.elsewhen(io.operation === DADAOExecOperation.AipSi.U) {
    resultLo := io.operandA + (io.operandB << 12)
    primaryCommit := true.B
    validOp := true.B
  }

  io.resultLo := resultLo
  io.resultHi := resultHi
  io.primaryCommit := primaryCommit
  io.validOp := validOp
}
