package dadao

import chisel3._
import chiseltest._
import org.scalatest.flatspec.AnyFlatSpec

final class DADAODecoderSpec extends AnyFlatSpec with ChiselScalatestTester {
  behavior of "DADAODecoder"

  private def setField(
      word: BigInt,
      offset: Int,
      value: BigInt,
      width: Int = 6
  ): BigInt = {
    val mask = ((BigInt(1) << width) - 1) << offset
    (word & ~mask) | ((value << offset) & mask)
  }

  private def fieldValue(
      word: BigInt,
      offset: Int,
      width: Int = 6
  ): BigInt =
    (word >> offset) & ((BigInt(1) << width) - 1)

  private def checkIllegal(
      word: BigInt,
      check: DADAODecoderStaticCheckEntry
  ): Boolean = {
    val fieldA = fieldValue(word, check.fieldA)
    val fieldB = fieldValue(word, check.fieldB)
    val fieldC = fieldValue(word, check.fieldC)
    check.kind match {
      case DADAOStaticCheckKind.DestNotZero =>
        fieldA == 0
      case DADAOStaticCheckKind.DualDestinationDistinct =>
        (fieldA == 0 && fieldB == 0) ||
          (fieldA == fieldB && fieldA != 0)
      case DADAOStaticCheckKind.RetRd0ImmediateZero =>
        fieldA == 0 && (word & ((BigInt(1) << 18) - 1)) != 0
      case DADAOStaticCheckKind.CountNonzero =>
        fieldA == 0
      case DADAOStaticCheckKind.RangeLimit64 =>
        fieldA + fieldB > 64
      case DADAOStaticCheckKind.RangeOverlap =>
        fieldA < fieldB + fieldC &&
          fieldB < fieldA + fieldC
      case DADAOStaticCheckKind.CountAtMost =>
        fieldA > check.limit
      case DADAOStaticCheckKind.CountEquals =>
        fieldA != check.limit
      case DADAOStaticCheckKind.FixedBitsZero =>
        (word & check.limit) != 0
      case DADAOStaticCheckKind.CfxNotReserved =>
        (fieldA >= 6 && fieldA <= 14) ||
          (fieldA >= 19 && fieldA <= 61)
      case other =>
        fail(s"unsupported static check kind $other")
    }
  }

  private def findCheck(kind: Int): DADAODecoderStaticCheckEntry =
    DADAODecoderTable.staticChecks.find(_.kind == kind).getOrElse {
      fail(s"no static check of kind $kind")
    }

  private def expectStaticFault(
      word: BigInt,
      reason: Int
  ): Unit = {
    test(new DADAODecoder) { dut =>
      dut.io.word.poke(word.U(32.W))
      dut.io.control.valid.expect(true.B)
      dut.io.control.isM1.expect(true.B)
      dut.io.control.fault.expect(true.B)
      dut.io.control.faultCode.expect(DADAOFaultCode.Illi.U)
      dut.io.control.debugFaultReason.expect(reason.U)
    }
  }

  private def expectStaticPass(word: BigInt): Unit = {
    test(new DADAODecoder) { dut =>
      dut.io.word.poke(word.U(32.W))
      dut.io.control.valid.expect(true.B)
      dut.io.control.isM1.expect(true.B)
      dut.io.control.fault.expect(false.B)
      dut.io.control.faultCode.expect(DADAOFaultCode.None.U)
      dut.io.control.debugFaultReason.expect(
        DADAODebugFaultReason.None.U
      )
    }
  }

  it should "decode every defined opcode entry" in {
    test(new DADAODecoder) { dut =>
      DADAODecoderTable.entries.zipWithIndex.foreach {
        case (entry, index) =>
          dut.io.word.poke(entry.value.U(32.W))
          dut.io.control.valid.expect(true.B)
          dut.io.decoded.id.expect(index.U)
          dut.io.decoded.format.expect(entry.format.U)
          dut.io.control.scope.expect(entry.scope.U)

          if (entry.scope == DADAOScope.M1) {
            val checks =
              DADAODecoderTable.staticChecks.filter(_.id == index)
            val operandFault = checks.exists { check =>
              DADAOStaticCheckKind.operandKinds.contains(check.kind) &&
              checkIllegal(entry.value, check)
            }
            val fieldFault = checks.exists { check =>
              !DADAOStaticCheckKind.operandKinds.contains(check.kind) &&
              checkIllegal(entry.value, check)
            }
            val expectedFault = operandFault || fieldFault
            dut.io.control.fault.expect(expectedFault.B)
            dut.io.control.faultCode.expect(
              (if (expectedFault) {
                 DADAOFaultCode.Illi
               } else {
                 DADAOFaultCode.None
               }).U
            )
            dut.io.control.debugFaultReason.expect(
              (if (operandFault) {
                 DADAODebugFaultReason.IlliOperand
               } else if (fieldFault) {
                 DADAODebugFaultReason.IlliField
               } else {
                 DADAODebugFaultReason.None
               }).U
            )
          } else {
            dut.io.control.fault.expect(true.B)
            dut.io.control.faultCode.expect(DADAOFaultCode.Illi.U)
            dut.io.control.unsupported.expect(true.B)
          }
      }
    }
  }

  it should "classify swym as the M1 no-op" in {
    test(new DADAODecoder) { dut =>
      val swym = DADAODecoderTable.entries(DADAODecoderTable.swymId)
      dut.io.word.poke(swym.value.U(32.W))
      dut.io.control.valid.expect(true.B)
      dut.io.control.isM1.expect(true.B)
      dut.io.control.isNoop.expect(true.B)
      dut.io.control.fault.expect(false.B)
    }
  }

  it should "classify an unmatched word as UNDI" in {
    test(new DADAODecoder) { dut =>
      dut.io.word.poke(0.U)
      dut.io.control.valid.expect(false.B)
      dut.io.control.fault.expect(true.B)
      dut.io.control.faultCode.expect(DADAOFaultCode.Undi.U)
      dut.io.control.debugFaultReason
        .expect(DADAODebugFaultReason.UndiReserved.U)
    }
  }

  it should "enumerate only M1 static checks" in {
    assert(DADAODecoderTable.staticChecks.nonEmpty)
    assert(
      DADAODecoderTable.staticChecks.forall { check =>
        DADAODecoderTable.entries(check.id).scope == DADAOScope.M1
      }
    )
  }

  it should "reject reserved CFX identifiers and escape SBZ bits" in {
    val trap =
      DADAODecoderTable.entries(
        DADAODecoderTable.ids.indexOf("trap_ciii_cfx")
      )
    Seq(5, 15, 18, 62, 63).foreach { cfxha =>
      expectStaticPass(setField(trap.value, 18, cfxha))
    }
    Seq(6, 14, 19, 61).foreach { cfxha =>
      expectStaticFault(
        setField(trap.value, 18, cfxha),
        DADAODebugFaultReason.IlliField
      )
    }

    val escape =
      DADAODecoderTable.entries(
        DADAODecoderTable.ids.indexOf("escape_ciii_cfx")
      )
    expectStaticPass(setField(escape.value, 0, 1, 18))
    expectStaticFault(
      setField(escape.value, 1, 1, 17),
      DADAODebugFaultReason.IlliField
    )
  }

  it should "match the independent full-field decoder oracle" in {
    assert(
      DADAODecoderOracleTable.entries.size ==
        DADAODecoderTable.entries.size
    )
    assert(
      DADAODecoderOracleTable.formatNames ==
        DADAODecoderTable.formatNames
    )

    test(new DADAODecoder) { dut =>
      DADAODecoderOracleTable.entries.foreach { expected =>
        dut.io.word.poke(expected.word.U(32.W))
        dut.io.decoded.word.expect(expected.word.U(32.W))
        dut.io.decoded.id.expect(expected.id.U)
        dut.io.decoded.format.expect(expected.format.U)
        dut.io.decoded.slot0.expect(expected.slot0.U)
        dut.io.decoded.slot1.expect(expected.slot1.U)
        dut.io.decoded.slot2.expect(expected.slot2.U)
        dut.io.decoded.slot3.expect(expected.slot3.U)
        dut.io.decoded.imm12.expect(expected.imm12.U)
        dut.io.decoded.imm18.expect(expected.imm18.U)
        dut.io.decoded.imm24.expect(expected.imm24.U)

        dut.io.control.valid.expect(true.B)
        dut.io.control.isM1.expect(
          (expected.scope == DADAOScope.M1).B
        )
        dut.io.control.scope.expect(expected.scope.U)
        dut.io.control.isNoop.expect(expected.isNoop.B)
        dut.io.control.fault.expect(expected.fault.B)
        dut.io.control.faultCode.expect(expected.faultCode.U)
        dut.io.control.debugFaultReason.expect(
          expected.debugReason.U
        )
        dut.io.control.unsupported.expect(
          expected.unsupported.B
        )
      }
    }
  }

  it should "reject rd0 and rb0 destinations as illegal operands" in {
    val rdCheck = findCheck(DADAOStaticCheckKind.DestNotZero)
    val rdWord = DADAODecoderTable.entries(rdCheck.id).value
    expectStaticFault(
      setField(rdWord, rdCheck.fieldA, 0),
      DADAODebugFaultReason.IlliOperand
    )

    val rbCheck = DADAODecoderTable.staticChecks.find { check =>
      check.kind == DADAOStaticCheckKind.DestNotZero &&
      DADAODecoderTable.ids(check.id).endsWith("_rb")
    }.getOrElse {
      fail("no rb0 destination static check")
    }
    val rbWord = DADAODecoderTable.entries(rbCheck.id).value
    expectStaticFault(
      setField(rbWord, rbCheck.fieldA, 0),
      DADAODebugFaultReason.IlliOperand
    )
  }

  it should "reject dual-destination conflicts" in {
    val check =
      findCheck(DADAOStaticCheckKind.DualDestinationDistinct)
    val word = DADAODecoderTable.entries(check.id).value
    val conflict = setField(
      setField(word, check.fieldA, 7),
      check.fieldB,
      7
    )
    expectStaticFault(
      conflict,
      DADAODebugFaultReason.IlliOperand
    )
    expectStaticFault(
      setField(
        setField(word, check.fieldA, 0),
        check.fieldB,
        0
      ),
      DADAODebugFaultReason.IlliOperand
    )
    expectStaticPass(
      setField(
        setField(word, check.fieldA, 1),
        check.fieldB,
        2
      )
    )
  }

  it should "reject ret rd0 with a nonzero immediate" in {
    val check = findCheck(DADAOStaticCheckKind.RetRd0ImmediateZero)
    val word = DADAODecoderTable.entries(check.id).value
    val illegalWord =
      setField(word, check.fieldA, 0) | BigInt(1)
    expectStaticFault(
      illegalWord,
      DADAODebugFaultReason.IlliOperand
    )
  }

  it should "reject zero-count and range-overflow block operations" in {
    val zeroCheck = findCheck(DADAOStaticCheckKind.CountNonzero)
    val zeroWord = DADAODecoderTable.entries(zeroCheck.id).value
    expectStaticFault(
      setField(zeroWord, zeroCheck.fieldA, 0),
      DADAODebugFaultReason.IlliOperand
    )

    val stmId =
      DADAODecoderTable.ids.indexOf("stm.b_rrri_rd")
    val overflowCheck =
      DADAODecoderTable.staticChecks.find { check =>
        check.id == stmId &&
        check.kind == DADAOStaticCheckKind.RangeLimit64
      }.getOrElse {
        fail("no stm range-overflow static check")
      }
    val overflowWord =
      DADAODecoderTable.entries(overflowCheck.id).value
    val legalBoundary = setField(
      setField(overflowWord, overflowCheck.fieldA, 62),
      overflowCheck.fieldB,
      2
    )
    expectStaticPass(legalBoundary)
    val illegalOverflow = setField(
      setField(overflowWord, overflowCheck.fieldA, 63),
      overflowCheck.fieldB,
      2
    )
    expectStaticFault(
      illegalOverflow,
      DADAODebugFaultReason.IlliOperand
    )
  }

  it should "reject overlapping register ranges" in {
    val rd2rdId =
      DADAODecoderTable.ids.indexOf("rd2rd_orri_rd")
    val check = DADAODecoderTable.staticChecks.find { candidate =>
      candidate.id == rd2rdId &&
      candidate.kind == DADAOStaticCheckKind.RangeOverlap
    }.getOrElse {
      fail("no rd2rd range-overlap static check")
    }
    val word = DADAODecoderTable.entries(check.id).value
    val legalBase = setField(
      setField(
        setField(word, check.fieldC, 2),
        check.fieldA,
        1
      ),
      check.fieldB,
      3
    )
    expectStaticPass(legalBase)
    val overlap = setField(
      setField(
        setField(word, check.fieldC, 2),
        check.fieldA,
        1
      ),
      check.fieldB,
      1
    )
    expectStaticFault(
      overlap,
      DADAODebugFaultReason.IlliOperand
    )
  }

  it should "reject shift-count field-limit violations" in {
    val limitCheck = DADAODecoderTable.staticChecks.find { check =>
      check.kind == DADAOStaticCheckKind.CountAtMost
    }.getOrElse {
      fail("no count-limit static check")
    }
    val baseLimitWord =
      DADAODecoderTable.entries(limitCheck.id).value
    val legalLimitWord =
      DADAODecoderTable.staticChecks
        .filter(_.id == limitCheck.id)
        .foldLeft(baseLimitWord) { (word, check) =>
          if (check.kind == DADAOStaticCheckKind.DestNotZero) {
            setField(word, check.fieldA, 1)
          } else {
            word
          }
        }
    val legalLimit = setField(
      legalLimitWord,
      limitCheck.fieldA,
      limitCheck.limit
    )
    expectStaticPass(legalLimit)
    val badLimit = setField(
      legalLimitWord,
      limitCheck.fieldA,
      limitCheck.limit + 1
    )
    expectStaticFault(
      badLimit,
      DADAODebugFaultReason.IlliField
    )
  }

  it should "keep a legal encoded instruction free of static faults" in {
    val legal =
      DADAODecoderTable.entries(DADAODecoderTable.swymId).value
    expectStaticPass(legal)
  }

  it should "keep non-M1 encodings within the unsupported-scope fault path" in {
    val fenceId =
      DADAODecoderTable.ids.indexWhere(_.startsWith("fence"))
    val fence = DADAODecoderTable.entries(fenceId)
    val sbzViolation = fence.value | (BigInt(1) << 4)

    test(new DADAODecoder) { dut =>
      dut.io.word.poke(sbzViolation.U(32.W))
      dut.io.control.valid.expect(true.B)
      dut.io.control.isM1.expect(false.B)
      dut.io.control.fault.expect(true.B)
      dut.io.control.faultCode.expect(DADAOFaultCode.Illi.U)
      dut.io.control.debugFaultReason.expect(
        DADAODebugFaultReason.IlliScopeM3.U
      )
    }
  }
}
