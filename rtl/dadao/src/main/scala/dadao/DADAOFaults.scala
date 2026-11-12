package dadao

object DADAOFaultCode {
  val None: Int = 0x00
  val Unmapped: Int = 0x87
  val Illi: Int = 0x88
  val Undi: Int = 0x89
  val Rasof: Int = 0x8a
  val Rasuf: Int = 0x8b
  val Malign: Int = 0x8c
  val Ialign: Int = 0x8d
}

object DADAODebugFaultReason {
  val None: Int = 0
  val IlliOperand: Int = 1
  val IlliField: Int = 2
  val IlliScopeFp: Int = 3
  val IlliScopeExcluded: Int = 4
  val IlliScopeM3: Int = 5
  val UndiReserved: Int = 6
  val AccessFault: Int = 7
}

object DADAOScope {
  val M1: Int = 0
  val Fp: Int = 1
  val Excluded: Int = 2
  val M3: Int = 3
}

object DADAOMemKind {
  val Fetch: Int = 0
  val Data: Int = 1
}

object DADAOMemOwner {
  val Idle: Int = 0
  val Fetch: Int = 1
  val Data: Int = 2
  val Ras: Int = 3
}

object DADAOMemSize {
  val Byte: Int = 0
  val Wyde: Int = 1
  val Tetra: Int = 2
  val Octa: Int = 3
}

object DADAOStaticCheckKind {
  val DestNotZero: Int = 1
  val DualDestinationDistinct: Int = 2
  val RetRd0ImmediateZero: Int = 3
  val CountNonzero: Int = 4
  val RangeLimit64: Int = 5
  val RangeOverlap: Int = 6
  val CountAtMost: Int = 7
  val CountEquals: Int = 8
  val FixedBitsZero: Int = 9
  val CfxNotReserved: Int = 10

  val operandKinds: Set[Int] = Set(
    DestNotZero,
    DualDestinationDistinct,
    RetRd0ImmediateZero,
    CountNonzero,
    RangeLimit64,
    RangeOverlap
  )
}
