package dadao

import chisel3._
import chisel3.util.{Cat, MuxLookup}

object DADAOByteLane {
  val BeatBytes: Int = 8

  def sizeBytes(size: UInt): UInt =
    (1.U(4.W) << size)(3, 0)

  def laneMask(addrLow: UInt, size: UInt): UInt = {
    val bytes = sizeBytes(size)
    val byteMask = ((1.U(9.W) << bytes) - 1.U)(7, 0)
    (byteMask << addrLow)(7, 0)
  }

  private def addressedByte(data: UInt, addressOffset: UInt): UInt =
    MuxLookup(addressOffset, 0.U(8.W))(
      Seq.tabulate(BeatBytes) { offset =>
        offset.U -> data(
          (BeatBytes - 1 - offset) * 8 + 7,
          (BeatBytes - 1 - offset) * 8
        )
      }
    )

  /**
    * Extract a right-aligned load value from an aligned big-endian beat.
    */
  def readValue(
      data: UInt,
      addrLow: UInt,
      size: UInt
  ): UInt = {
    val bytes = sizeBytes(size)
    val firstResultByte = BeatBytes.U - bytes
    val resultBytes = Seq.tabulate(BeatBytes) { outputIndex =>
      val resultIndex = outputIndex.U - firstResultByte
      val guestOffset = addrLow + resultIndex
      Mux(
        outputIndex.U >= firstResultByte &&
          guestOffset < BeatBytes.U,
        addressedByte(data, guestOffset),
        0.U(8.W)
      )
    }
    Cat(resultBytes)
  }

  /**
    * Merge a right-aligned store value into an aligned big-endian beat.
    */
  def mergeWrite(
      oldData: UInt,
      writeData: UInt,
      addrLow: UInt,
      size: UInt,
      writeStrobe: UInt
  ): UInt = {
    val bytes = sizeBytes(size)
    val writeMask = laneMask(addrLow, size) & writeStrobe
    val resultBytes = Seq.tabulate(BeatBytes) { guestIndex =>
      val relative = guestIndex.U - addrLow
      val sourceOffset = (BeatBytes.U - bytes) + relative
      val replacement = addressedByte(writeData, sourceOffset)
      val original = addressedByte(oldData, guestIndex.U)

      Mux(
        writeMask(guestIndex),
        replacement,
        original
      )
    }
    Cat(resultBytes)
  }
}
