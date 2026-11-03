package dadao

final class DADAOTestUartFrameException(
    val reason: String,
    detail: String = ""
) extends IllegalArgumentException(
      if (detail.isEmpty) reason else s"$reason: $detail"
    )

final case class DADAOTestUartFrame(
    frameType: String,
    sequence: Int,
    address: BigInt,
    payload: Array[Byte]
)

object DADAOTestUartFrame {
  val Magic: Array[Byte] = Array('D', 'D', 'A', 'O').map(_.toByte)
  val Version: Int = 1
  val HeaderBytes: Int = 20
  val CrcBytes: Int = 4
  val MinimumFrameBytes: Int = HeaderBytes + CrcBytes

  val typeCodes: Map[String, Int] = Map(
    "load" -> 0x01,
    "run" -> 0x02,
    "result" -> 0x03,
    "error" -> 0x7f
  )
  private val typeNames: Map[Int, String] =
    typeCodes.map { case (name, code) => code -> name }

  private val AddressLimit = BigInt(1) << 64
  private val CrcPolynomial = 0xedb88320L

  def encode(
      frameType: String,
      sequence: Int,
      address: BigInt,
      payload: Array[Byte] = Array.emptyByteArray
  ): Array[Byte] = {
    val typeCode = typeCodes.getOrElse(
      frameType.toLowerCase,
      throw new DADAOTestUartFrameException(
        "unknown-type",
        frameType
      )
    )
    requireField(sequence >= 0 && sequence <= 0xffff, "sequence")
    requireField(
      address >= 0 && address < AddressLimit,
      "address"
    )

    val bytes = new Array[Byte](
      HeaderBytes + payload.length + CrcBytes
    )
    Array.copy(Magic, 0, bytes, 0, Magic.length)
    bytes(4) = Version.toByte
    bytes(5) = typeCode.toByte
    writeUInt(bytes, 6, sequence, 2)
    writeUInt(bytes, 8, address, 8)
    writeUInt(bytes, 16, payload.length, 4)
    Array.copy(payload, 0, bytes, HeaderBytes, payload.length)

    val crc = crc32(
      bytes.slice(4, HeaderBytes + payload.length)
    )
    writeUInt(bytes, HeaderBytes + payload.length, crc, CrcBytes)
    bytes
  }

  def decode(bytes: Array[Byte]): DADAOTestUartFrame = {
    if (bytes.length < MinimumFrameBytes) {
      throw new DADAOTestUartFrameException(
        "truncated",
        s"got ${bytes.length} bytes, need at least $MinimumFrameBytes"
      )
    }
    if (!bytes.slice(0, Magic.length).sameElements(Magic)) {
      throw new DADAOTestUartFrameException(
        "bad-magic",
        bytes.slice(0, Magic.length).map("%02x".format(_)).mkString
      )
    }

    val version = bytes(4) & 0xff
    if (version != Version) {
      throw new DADAOTestUartFrameException(
        "bad-version",
        version.toString
      )
    }

    val typeCode = bytes(5) & 0xff
    val frameType = typeNames.getOrElse(
      typeCode,
      throw new DADAOTestUartFrameException(
        "unknown-type",
        typeCode.toString
      )
    )
    val sequence = readUInt(bytes, 6, 2).toInt
    val address = readUInt(bytes, 8, 8)
    val lengthValue = readUInt(bytes, 16, 4)
    if (lengthValue > Int.MaxValue) {
      throw new DADAOTestUartFrameException(
        "length-overflow",
        lengthValue.toString
      )
    }
    val length = lengthValue.toInt
    val expectedLength = HeaderBytes + length + CrcBytes
    if (bytes.length != expectedLength) {
      throw new DADAOTestUartFrameException(
        "length-mismatch",
        s"header says $expectedLength, got ${bytes.length}"
      )
    }

    val payload = bytes.slice(
      HeaderBytes,
      HeaderBytes + length
    )
    val receivedCrc =
      readUInt(bytes, HeaderBytes + length, CrcBytes).toLong
    val expectedCrc = crc32(
      bytes.slice(4, HeaderBytes + length)
    )
    if (receivedCrc != expectedCrc) {
      throw new DADAOTestUartFrameException(
        "crc-mismatch",
        f"expected $expectedCrc%08x, got $receivedCrc%08x"
      )
    }

    DADAOTestUartFrame(
      frameType = frameType,
      sequence = sequence,
      address = address,
      payload = payload
    )
  }

  def crc32(bytes: Array[Byte]): Long = {
    var crc = 0xffffffffL
    for (value <- bytes) {
      crc ^= value.toLong & 0xffL
      for (_ <- 0 until 8) {
        crc =
          if ((crc & 1L) != 0L) {
            (crc >>> 1) ^ CrcPolynomial
          } else {
            crc >>> 1
          }
      }
    }
    (~crc) & 0xffffffffL
  }

  private def requireField(condition: Boolean, field: String): Unit = {
    if (!condition) {
      throw new DADAOTestUartFrameException(
        "field-range",
        field
      )
    }
  }

  private def writeUInt(
      target: Array[Byte],
      offset: Int,
      value: BigInt,
      width: Int
  ): Unit = {
    val limit = BigInt(1) << (width * 8)
    requireField(value >= 0 && value < limit, s"field@$offset")
    for (index <- 0 until width) {
      val shift = (width - 1 - index) * 8
      target(offset + index) =
        ((value >> shift) & 0xff).toByte
    }
  }

  private def readUInt(
      source: Array[Byte],
      offset: Int,
      width: Int
  ): BigInt = {
    var value = BigInt(0)
    for (index <- 0 until width) {
      value =
        (value << 8) | BigInt(source(offset + index) & 0xff)
    }
    value
  }
}
