package dadao

import chisel3._
import chiseltest._
import org.scalatest.flatspec.AnyFlatSpec

final class DADAOReservedCellCoverageSpec
    extends AnyFlatSpec
    with ChiselScalatestTester {
  behavior of "DADAO reserved-cell coverage"

  it should "decode every reserved main and MISC cell as UNDI" in {
    assert(DADAOReservedCoverageTable.cells.nonEmpty)

    test(new DADAODecoder) { dut =>
      DADAOReservedCoverageTable.cells.foreach { cell =>
        dut.io.word.poke(cell.word.U(32.W))
        dut.io.control.valid.expect(false.B)
        dut.io.control.isM1.expect(false.B)
        dut.io.control.fault.expect(true.B)
        dut.io.control.faultCode.expect(DADAOFaultCode.Undi.U)
        dut.io.control.debugFaultReason.expect(
          DADAODebugFaultReason.UndiReserved.U
        )
      }
    }
  }

  it should "cover every reserved MISC subcell exactly once" in {
    val miscCells = DADAOReservedCoverageTable.cells.filter {
      _.domain.startsWith("OPC-")
    }
    assert(miscCells.nonEmpty)

    val unique = miscCells.map(cell => (cell.op, cell.cell)).toSet
    assert(unique.size == miscCells.size)
  }
}
