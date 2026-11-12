package dadao

import freechips.rocketchip.subsystem._
import org.chipsalliance.cde.config.Config

class WithDADAOTile(n: Int = 1) extends Config((site, here, up) => {
  case TilesLocated(InSubsystem) =>
    val previous = up(TilesLocated(InSubsystem), site)
    val idOffset = up(NumTiles)
    (0 until n).map { i =>
      DADAOTileAttachParams(
        tileParams = DADAOTileParams(tileId = i + idOffset),
        crossingParams = RocketCrossingParams()
      )
    } ++ previous
  case SystemBusKey =>
    up(SystemBusKey, site).copy(beatBytes = 8)
  case NumTiles =>
    up(NumTiles) + n
})

class DADAOConfig extends Config(
  new WithDADAOTile ++ new freechips.rocketchip.system.BaseConfig
)
