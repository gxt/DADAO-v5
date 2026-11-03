package dadao

import org.scalatest.flatspec.AnyFlatSpec

final class DADAOExecCoverageSpec extends AnyFlatSpec {
  behavior of "DADAOExecTable"

  it should "partition M1 exactly" in {
    assert(DADAOExecTable.rtl009Count == 106)
    assert(DADAOExecTable.swymCount == 1)
    assert(DADAOExecTable.memoryCount == 30)
    assert(DADAOExecTable.controlCount == 15)
    assert(DADAOExecTable.systemCount == 4)
    assert(
      DADAOExecTable.rtl009Count +
        DADAOExecTable.swymCount +
        DADAOExecTable.memoryCount +
        DADAOExecTable.controlCount +
        DADAOExecTable.systemCount == 156
    )
  }

  it should "cover every RTL-009t id exactly once" in {
    assert(DADAOExecTable.entries.size == 106)
    assert(DADAOExecTable.ids.size == 106)
    assert(DADAOExecTable.ids.distinct.size == 106)
    val entryIds = DADAOExecTable.entries.map(_.id)
    assert(entryIds.distinct.size == 106)
    assert(
      entryIds.forall(id => id >= 0 && id < DADAODecoderTable.entries.size)
    )
  }

  it should "describe source and destination references legally" in {
    DADAOExecTable.entries.foreach { entry =>
      assert(entry.dstCount >= 1 && entry.dstCount <= 2)
      assert(entry.srcCount >= 0 && entry.srcCount <= 3)

      val destinations = Seq(entry.dst0, entry.dst1).take(entry.dstCount)
      val sources = Seq(entry.src0, entry.src1, entry.src2).take(entry.srcCount)
      (destinations ++ sources).foreach { ref =>
        assert(ref.valid)
        assert(ref.bank >= DADAORegBank.Rd)
        assert(ref.bank <= DADAORegBank.Ra)
        assert(ref.width == 6)
        assert(ref.low >= 0)
        assert(ref.low + ref.width <= 24)
      }
    }
  }

  it should "encode read-modify-write and dual destinations" in {
    assert(DADAOExecTable.entries.count(_.destRead) == 6)
    assert(DADAOExecTable.entries.count(_.dstCount == 2) == 6)
  }

  it should "encode immediate and block-copy special modes" in {
    assert(
      DADAOExecTable.entries.count(
        _.special == DADAOExecSpecial.CopyBlock
      ) == 6
    )
    assert(
      DADAOExecTable.entries.count(
        _.special == DADAOExecSpecial.SetWyde
      ) == 7
    )
    assert(
      DADAOExecTable.entries.count(
        _.immMode == DADAOExecImmMode.Immu16Wyde
      ) == 7
    )
  }

  it should "keep all operation codes inside the generated enum" in {
    val supported = Set(
      DADAOExecOperation.Add,
      DADAOExecOperation.Sub,
      DADAOExecOperation.Mul,
      DADAOExecOperation.Div,
      DADAOExecOperation.Rem,
      DADAOExecOperation.Cmp,
      DADAOExecOperation.And,
      DADAOExecOperation.Or,
      DADAOExecOperation.Xor,
      DADAOExecOperation.Xnor,
      DADAOExecOperation.Shl,
      DADAOExecOperation.Shr,
      DADAOExecOperation.Ext,
      DADAOExecOperation.CsN,
      DADAOExecOperation.CsZ,
      DADAOExecOperation.CsP,
      DADAOExecOperation.CsEq,
      DADAOExecOperation.CsNe,
      DADAOExecOperation.SetOw,
      DADAOExecOperation.SetZeroWyde,
      DADAOExecOperation.OrW,
      DADAOExecOperation.AndnW,
      DADAOExecOperation.AipSi,
      DADAOExecOperation.CopyBlock
    )
    assert(
      DADAOExecTable.entries.map(_.operation).toSet == supported
    )
  }

  it should "cover every descriptor operation with ALU or IntExec tests" in {
    val aluTestedOperations =
      DADAOALUOracleTable.vectors.map(_.operation).toSet
    val nonCopyOperations = DADAOExecTable.entries
      .filter(_.special != DADAOExecSpecial.CopyBlock)
      .map(_.operation)
      .toSet
    assert(nonCopyOperations.subsetOf(aluTestedOperations))
    assert(
      DADAOExecTable.entries.exists(
        _.special == DADAOExecSpecial.CopyBlock
      )
    )
  }
}
