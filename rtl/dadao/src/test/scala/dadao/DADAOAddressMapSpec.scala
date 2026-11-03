package dadao

import chisel3._
import chiseltest._
import org.scalatest.flatspec.AnyFlatSpec

final class DADAOAddressMapSpec
    extends AnyFlatSpec
    with ChiselScalatestTester {
  behavior of "DADAOAccessCheck"

  private val params = DADAOParams()
  private val legacyExitBase = BigInt("ffff80000000", 16)
  private val ramEnd = params.ramBase + params.ramSize
  private val bootRomEnd = params.bootRomBase + params.bootRomSize

  private def expectAccess(
      dut: DADAOAccessCheck,
      address: BigInt,
      write: Boolean,
      size: Int,
      kind: Int,
      expectedRegion: Int,
      expectedMapped: Boolean,
      expectedAllowed: Boolean,
      expectedFaultCode: Int
  ): Unit = {
    dut.io.addr.poke(address.U)
    dut.io.write.poke(write.B)
    dut.io.size.poke(size.U)
    dut.io.kind.poke(kind.U)
    dut.clock.step()

    dut.io.region.expect(expectedRegion.U)
    dut.io.mapped.expect(expectedMapped.B)
    dut.io.allowed.expect(expectedAllowed.B)
    dut.io.fault.expect((expectedFaultCode != DADAOFaultCode.None).B)
    dut.io.faultCode.expect(expectedFaultCode.U)
  }

  it should "accept all aligned RAM loads, stores, and fetches" in {
    test(new DADAOAccessCheck(params)) { dut =>
      for (
        size <- Seq(
          DADAOMemSize.Byte,
          DADAOMemSize.Wyde,
          DADAOMemSize.Tetra,
          DADAOMemSize.Octa
        )
      ) {
        val bytes = 1 << size
        expectAccess(
          dut,
          params.ramBase,
          write = false,
          size,
          DADAOMemKind.Data,
          DADAOMemoryRegion.Ram,
          expectedMapped = true,
          expectedAllowed = true,
          DADAOFaultCode.None
        )
        expectAccess(
          dut,
          ramEnd - bytes,
          write = true,
          size,
          DADAOMemKind.Data,
          DADAOMemoryRegion.Ram,
          expectedMapped = true,
          expectedAllowed = true,
          DADAOFaultCode.None
        )
      }

      expectAccess(
        dut,
        params.ramBase + 0x20,
        write = false,
        DADAOMemSize.Tetra,
        DADAOMemKind.Fetch,
        DADAOMemoryRegion.Ram,
        expectedMapped = true,
        expectedAllowed = true,
        DADAOFaultCode.None
      )
    }
  }

  it should "accept BootROM loads and fetches but reject stores" in {
    test(new DADAOAccessCheck(params)) { dut =>
      expectAccess(
        dut,
        params.bootRomBase,
        write = false,
        DADAOMemSize.Octa,
        DADAOMemKind.Data,
        DADAOMemoryRegion.BootRom,
        expectedMapped = true,
        expectedAllowed = true,
        DADAOFaultCode.None
      )
      expectAccess(
        dut,
        bootRomEnd - 4,
        write = false,
        DADAOMemSize.Tetra,
        DADAOMemKind.Fetch,
        DADAOMemoryRegion.BootRom,
        expectedMapped = true,
        expectedAllowed = true,
        DADAOFaultCode.None
      )
      expectAccess(
        dut,
        params.bootRomBase,
        write = true,
        DADAOMemSize.Octa,
        DADAOMemKind.Data,
        DADAOMemoryRegion.BootRom,
        expectedMapped = true,
        expectedAllowed = false,
        DADAOFaultCode.Illi
      )
    }
  }

  it should "report the full access range outside a region as unmapped" in {
    test(new DADAOAccessCheck(params)) { dut =>
      expectAccess(
        dut,
        ramEnd,
        write = false,
        DADAOMemSize.Byte,
        DADAOMemKind.Data,
        DADAOMemoryRegion.Unmapped,
        expectedMapped = false,
        expectedAllowed = false,
        DADAOFaultCode.Unmapped
      )
      expectAccess(
        dut,
        bootRomEnd - 4,
        write = false,
        DADAOMemSize.Octa,
        DADAOMemKind.Data,
        DADAOMemoryRegion.Unmapped,
        expectedMapped = false,
        expectedAllowed = false,
        DADAOFaultCode.Unmapped
      )
    }
  }

  it should "treat the removed Exit port and UART window as unmapped" in {
    test(new DADAOAccessCheck(params)) { dut =>
      expectAccess(
        dut,
        legacyExitBase,
        write = true,
        DADAOMemSize.Octa,
        DADAOMemKind.Data,
        DADAOMemoryRegion.Unmapped,
        expectedMapped = false,
        expectedAllowed = false,
        DADAOFaultCode.Unmapped
      )
      expectAccess(
        dut,
        params.uartBase,
        write = false,
        DADAOMemSize.Tetra,
        DADAOMemKind.Data,
        DADAOMemoryRegion.Unmapped,
        expectedMapped = false,
        expectedAllowed = false,
        DADAOFaultCode.Unmapped
      )
      expectAccess(
        dut,
        legacyExitBase,
        write = false,
        DADAOMemSize.Tetra,
        DADAOMemKind.Fetch,
        DADAOMemoryRegion.Unmapped,
        expectedMapped = false,
        expectedAllowed = false,
        DADAOFaultCode.Unmapped
      )
    }
  }

  it should "apply UNMAPPED, MALIGN, ILLI priority in order" in {
    test(new DADAOAccessCheck(params)) { dut =>
      expectAccess(
        dut,
        legacyExitBase + 1,
        write = true,
        DADAOMemSize.Wyde,
        DADAOMemKind.Data,
        DADAOMemoryRegion.Unmapped,
        expectedMapped = false,
        expectedAllowed = false,
        DADAOFaultCode.Unmapped
      )
      expectAccess(
        dut,
        params.bootRomBase + 1,
        write = true,
        DADAOMemSize.Wyde,
        DADAOMemKind.Data,
        DADAOMemoryRegion.BootRom,
        expectedMapped = true,
        expectedAllowed = false,
        DADAOFaultCode.Malign
      )
      expectAccess(
        dut,
        params.ramBase + 0x10,
        write = false,
        size = 4,
        DADAOMemKind.Data,
        DADAOMemoryRegion.Ram,
        expectedMapped = true,
        expectedAllowed = false,
        DADAOFaultCode.Illi
      )
      expectAccess(
        dut,
        params.ramBase + 0x20,
        write = false,
        DADAOMemSize.Byte,
        DADAOMemKind.Fetch,
        DADAOMemoryRegion.Ram,
        expectedMapped = true,
        expectedAllowed = false,
        DADAOFaultCode.Illi
      )
    }
  }
}
