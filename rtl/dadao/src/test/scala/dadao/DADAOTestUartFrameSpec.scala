package dadao

import org.scalatest.flatspec.AnyFlatSpec

final class DADAOTestUartFrameSpec extends AnyFlatSpec {
  behavior of "DADAOTestUartFrame"

  private val payload =
    Array[Byte]('D', 'D', 'A', 'O', 0xa5.toByte, 0x5a, 0x00, 0xff.toByte)
  private val address = BigInt("fc0000000000", 16)

  private def assertFailure(
      expectedReason: String
  )(operation: => Unit): Unit = {
    val error = intercept[DADAOTestUartFrameException] {
      operation
    }
    assert(
      error.reason == expectedReason,
      s"expected $expectedReason, got ${error.reason}"
    )
  }

  it should "round-trip the frozen frame format" in {
    val frame = DADAOTestUartFrame.encode(
      "load",
      0x1234,
      address,
      payload
    )
    val decoded = DADAOTestUartFrame.decode(frame)

    assert(decoded.frameType == "load")
    assert(decoded.sequence == 0x1234)
    assert(decoded.address == address)
    assert(decoded.payload.sameElements(payload))
  }

  it should "match the independent Python CRC32 value" in {
    val frame = DADAOTestUartFrame.encode(
      "load",
      0x1234,
      address,
      payload
    )
    val crcBytes = frame.takeRight(4)

    assert(
      crcBytes.sameElements(
        Array[Byte](0x05, 0x6f, 0x7a, 0xb6.toByte)
      )
    )
  }

  it should "reject bad magic and version" in {
    val frame = DADAOTestUartFrame.encode(
      "load",
      1,
      address,
      payload
    )

    val badMagic = frame.clone()
    badMagic(0) = (badMagic(0) ^ 0xff).toByte
    assertFailure("bad-magic") {
      DADAOTestUartFrame.decode(badMagic)
    }

    val badVersion = frame.clone()
    badVersion(4) = 2
    assertFailure("bad-version") {
      DADAOTestUartFrame.decode(badVersion)
    }
  }

  it should "reject unknown type and corrupted CRC" in {
    val frame = DADAOTestUartFrame.encode(
      "load",
      1,
      address,
      payload
    )

    val badType = frame.clone()
    badType(5) = 0x55
    assertFailure("unknown-type") {
      DADAOTestUartFrame.decode(badType)
    }

    val badCrc = frame.clone()
    badCrc(badCrc.length - 1) =
      (badCrc.last ^ 0x01).toByte
    assertFailure("crc-mismatch") {
      DADAOTestUartFrame.decode(badCrc)
    }
  }

  it should "reject truncation and trailing bytes" in {
    val frame = DADAOTestUartFrame.encode(
      "load",
      1,
      address,
      payload
    )

    assertFailure("truncated") {
      DADAOTestUartFrame.decode(frame.take(10))
    }
    assertFailure("length-mismatch") {
      DADAOTestUartFrame.decode(frame.dropRight(1))
    }
    assertFailure("length-mismatch") {
      DADAOTestUartFrame.decode(frame ++ Array[Byte](0))
    }
  }
}
