package dadao

import chisel3._
import chisel3.util.Decoupled

final class DADAOMemReq(val addrBits: Int, val dataBits: Int) extends Bundle {
  val addr = UInt(addrBits.W)
  val write = Bool()
  val size = UInt(3.W)
  val wdata = UInt(dataBits.W)
  val wstrb = UInt((dataBits / 8).W)
  val kind = UInt(2.W)
}

final class DADAOMemResp(val dataBits: Int) extends Bundle {
  val rdata = UInt(dataBits.W)
  val fault = Bool()
  val faultCode = UInt(8.W)
}

final class DADAOMemPort(val addrBits: Int, val dataBits: Int) extends Bundle {
  val req = Decoupled(new DADAOMemReq(addrBits, dataBits))
  val resp = Flipped(Decoupled(new DADAOMemResp(dataBits)))
}
