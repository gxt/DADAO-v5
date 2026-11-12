package dadao

import chisel3._
import chisel3.util.{Cat, Mux1H, MuxLookup}

final class DADAOControlSignals extends Bundle {
  val valid = Bool()
  val isM1 = Bool()
  val scope = UInt(2.W)
  val isNoop = Bool()
  val fault = Bool()
  val faultCode = UInt(8.W)
  val debugFaultReason = UInt(3.W)
  val unsupported = Bool()
}

final class DADAODecodedInstruction extends Bundle {
  val word = UInt(32.W)
  val id = UInt(9.W)
  val format = UInt(4.W)
  val slot0 = UInt(6.W)
  val slot1 = UInt(6.W)
  val slot2 = UInt(6.W)
  val slot3 = UInt(6.W)
  val imm12 = UInt(12.W)
  val imm18 = UInt(18.W)
  val imm24 = UInt(24.W)
}

final class DADAODecoderIO extends Bundle {
  val word = Input(UInt(32.W))
  val decoded = Output(new DADAODecodedInstruction)
  val control = Output(new DADAOControlSignals)
}

final class DADAODecoder extends Module {
  val io = IO(new DADAODecoderIO)

  private val table = DADAODecoderTable.entries
  private val matches = VecInit(
    table.map(entry => (io.word & entry.mask.U(32.W)) === entry.value.U(32.W))
  )
  private val hit = matches.asUInt.orR
  private val selected = Mux1H(
    matches,
    table.map(entry =>
      Cat(
        entry.id.U(9.W),
        entry.format.U(4.W),
        entry.scope.U(2.W)
      )
    )
  )

  private val selectedId = selected(14, 6)
  private val selectedFormat = selected(5, 2)
  private val selectedScope = selected(1, 0)

  private def fieldAt(offset: Int): UInt =
    io.word(offset + 5, offset)

  private def staticCheckIllegal(
      check: DADAODecoderStaticCheckEntry
  ): Bool = {
    val fieldA = fieldAt(check.fieldA)
    val fieldB = fieldAt(check.fieldB)
    val fieldC = fieldAt(check.fieldC)
    check.kind match {
      case DADAOStaticCheckKind.DestNotZero =>
        fieldA === 0.U
      case DADAOStaticCheckKind.DualDestinationDistinct =>
        (fieldA === 0.U && fieldB === 0.U) ||
          (fieldA === fieldB && fieldA =/= 0.U)
      case DADAOStaticCheckKind.RetRd0ImmediateZero =>
        fieldA === 0.U && io.word(17, 0) =/= 0.U
      case DADAOStaticCheckKind.CountNonzero =>
        fieldA === 0.U
      case DADAOStaticCheckKind.RangeLimit64 =>
        Cat(0.U(1.W), fieldA) + Cat(0.U(1.W), fieldB) > 64.U
      case DADAOStaticCheckKind.RangeOverlap =>
        fieldA < Cat(0.U(1.W), fieldB) + Cat(0.U(1.W), fieldC) &&
          fieldB < Cat(0.U(1.W), fieldA) + Cat(0.U(1.W), fieldC)
      case DADAOStaticCheckKind.CountAtMost =>
        fieldA > check.limit.U
      case DADAOStaticCheckKind.CountEquals =>
        fieldA =/= check.limit.U
      case DADAOStaticCheckKind.FixedBitsZero =>
        (io.word & check.limit.U(32.W)) =/= 0.U
      case DADAOStaticCheckKind.CfxNotReserved =>
        (fieldA >= 6.U && fieldA <= 14.U) ||
          (fieldA >= 19.U && fieldA <= 61.U)
      case other =>
        throw new IllegalArgumentException(
          s"unsupported static check kind: $other"
        )
    }
  }

  private val staticCheckFaults =
    DADAODecoderTable.staticChecks.map { check =>
      selectedId === check.id.U(9.W) &&
        staticCheckIllegal(check)
    }
  private val staticOperandFault = VecInit(
    DADAODecoderTable.staticChecks.zip(staticCheckFaults).map {
      case (check, fault) =>
        DADAOStaticCheckKind.operandKinds.contains(check.kind).B &&
          fault
    }
  ).asUInt.orR
  private val staticFieldFault = VecInit(
    DADAODecoderTable.staticChecks.zip(staticCheckFaults).map {
      case (check, fault) =>
        !DADAOStaticCheckKind.operandKinds.contains(check.kind).B &&
          fault
    }
  ).asUInt.orR
  private val staticFault = staticOperandFault || staticFieldFault

  io.decoded.word := io.word
  io.decoded.id := selectedId
  io.decoded.format := selectedFormat
  io.decoded.slot0 := io.word(23, 18)
  io.decoded.slot1 := io.word(17, 12)
  io.decoded.slot2 := io.word(11, 6)
  io.decoded.slot3 := io.word(5, 0)
  io.decoded.imm12 := io.word(11, 0)
  io.decoded.imm18 := io.word(17, 0)
  io.decoded.imm24 := io.word(23, 0)

  private val isM1 = hit && selectedScope === DADAOScope.M1.U
  private val isNoop =
    hit && selectedId === DADAODecoderTable.swymId.U(8.W)
  private val scopeReason = MuxLookup(
    selectedScope,
    DADAODebugFaultReason.IlliScopeExcluded.U
  )(
    Seq(
      DADAOScope.Fp.U -> DADAODebugFaultReason.IlliScopeFp.U,
      DADAOScope.Excluded.U -> DADAODebugFaultReason.IlliScopeExcluded.U,
      DADAOScope.M3.U -> DADAODebugFaultReason.IlliScopeM3.U
    )
  )

  io.control.valid := hit
  io.control.isM1 := isM1
  io.control.scope := selectedScope
  io.control.isNoop := isNoop
  io.control.fault := !hit || !isM1 || staticFault
  io.control.faultCode := Mux(
    !hit,
    DADAOFaultCode.Undi.U(8.W),
    Mux(
      !isM1 || staticFault,
      DADAOFaultCode.Illi.U(8.W),
      DADAOFaultCode.None.U(8.W)
    )
  )
  io.control.debugFaultReason := Mux(
    !hit,
    DADAODebugFaultReason.UndiReserved.U(3.W),
    Mux(
      !isM1,
      scopeReason,
      Mux(
        staticOperandFault,
        DADAODebugFaultReason.IlliOperand.U(3.W),
        Mux(
          staticFieldFault,
          DADAODebugFaultReason.IlliField.U(3.W),
          DADAODebugFaultReason.None.U(3.W)
        )
      )
    )
  )
  io.control.unsupported := !isM1
}
