package dadao

import circt.stage.ChiselStage
import chisel3._
import freechips.rocketchip.diplomacy._
import freechips.rocketchip.prci.SynchronousCrossing
import freechips.rocketchip.subsystem.{InSubsystem, TilesLocated}
import freechips.rocketchip.tile.PriorityMuxHartIdFromSeq
import java.nio.charset.StandardCharsets
import java.nio.file.{Files, Paths}
import org.chipsalliance.cde.config.Parameters

final class DADAOTop(
    params: DADAOTileParams = DADAOTileParams()
) (implicit p: Parameters) extends LazyModule {
  val hartIdSource =
    BundleBridgeSource[UInt](() => UInt(64.W))
  val resetVectorSource =
    BundleBridgeSource[UInt](() => UInt(params.dadao.addrBits.W))

  val tile = LazyModule(
    new DADAOTile(
      params,
      SynchronousCrossing(),
      PriorityMuxHartIdFromSeq(Seq(params)),
      p
    )
  )
  tile.hartIdNode := hartIdSource
  tile.resetVectorNode := resetVectorSource

  override lazy val module = new LazyModuleImp(this) {
    val io = IO(new Bundle {
      val pc = Output(UInt(params.dadao.addrBits.W))
    })

    hartIdSource.bundle := params.tileId.U
    resetVectorSource.bundle := params.dadao.resetVector.U
    io.pc := tile.module.io.pc
  }
}

object DADAOElaborator {
  def main(args: Array[String]): Unit = {
    implicit val p: Parameters = Parameters.empty

    val configParameters = new DADAOConfig().toInstance
    val attachedTiles = configParameters(TilesLocated(InSubsystem))
    require(
      attachedTiles.exists(_.isInstanceOf[DADAOTileAttachParams]),
      "DADAOConfig did not attach a DADAOTile"
    )
    println(s"DADAOConfig attached ${attachedTiles.size} tile(s)")

    val top = LazyModule(new DADAOTop())
    val chirrtl = ChiselStage.emitCHIRRTL(
      top.module
    )

    require(
      chirrtl.nonEmpty,
      "DADAO elaboration produced empty CHIRRTL"
    )

    val output =
      if (args.nonEmpty) Paths.get(args(0))
      else Paths.get("build/dadao/DADAOTop.fir")
    val absolute = output.toAbsolutePath
    val parent = absolute.getParent
    if (parent != null) {
      Files.createDirectories(parent)
    }
    Files.write(absolute, chirrtl.getBytes(StandardCharsets.UTF_8))
    println(
      s"DADAO elaboration wrote ${chirrtl.length} characters to $absolute"
    )
  }
}
