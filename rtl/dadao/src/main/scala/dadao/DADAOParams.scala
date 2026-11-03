package dadao

final case class DADAOParams(
    xlen: Int = 64,
    addrBits: Int = 64,
    dataBits: Int = 64,
    resetVector: BigInt = BigInt("ffffffff0000", 16),
    ramBase: BigInt = BigInt("fc0000000000", 16),
    ramSize: BigInt = BigInt("1000000", 16),
    bootRomBase: BigInt = BigInt("ffffffff0000", 16),
    bootRomSize: BigInt = BigInt("10000", 16),
    uartBase: BigInt = BigInt("ffff90000000", 16),
    uartSize: BigInt = BigInt("1000", 16)
) {
  require(xlen == 64, "M1 DADAO core currently requires xlen = 64")
  require(addrBits >= 48, "address width must represent the M1 48-bit address map")
  require(dataBits == 64, "initial DADAO memory interface requires a 64-bit data path")
  require(resetVector == bootRomBase, "reset vector must remain the boot ROM base")
  require(bootRomSize == BigInt("10000", 16), "BootROM must remain 64 KiB")
  require(uartSize == BigInt("1000", 16), "UART reservation must remain 4 KiB")
}
