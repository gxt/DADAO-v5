package dadao

import chisel3._
import chisel3.util.{Cat, MuxLookup}

object DADAOCfxCode {
  val Umom: Int = 0
  val Jmon: Int = 1
  val Smon: Int = 2
  val Hmon: Int = 3
  val Power: Int = 63
}

object DADAORunMode {
  val User: Int = 0
  val Jail: Int = 1
  val Supv: Int = 2
  val Hypv: Int = 3
}

object DADAOCfxCause {
  val Trap: BigInt = BigInt(1) << 0
  val Mem: BigInt = BigInt(1) << 1
  val Reg: BigInt = BigInt(1) << 2
  val Esc: BigInt = BigInt(1) << 3
  val Perm: BigInt = BigInt(1) << 7
  val Illi: BigInt = BigInt(1) << 8
}

final class DADAOCfxTestWrite extends Bundle {
  val valid = Bool()
  val cfxha = UInt(6.W)
  val cg = UInt(6.W)
  val rc = UInt(6.W)
  val data = UInt(64.W)
}

final class DADAOCfxTestRead extends Bundle {
  val cfxha = UInt(6.W)
  val cg = UInt(6.W)
  val rc = UInt(6.W)
}

final class DADAOCfxStatus extends Bundle {
  val runMode = UInt(2.W)
  val cfxCode = UInt(6.W)
  val cfxMask = UInt(64.W)
}

final class DADAOCfxStatusSet extends Bundle {
  val valid = Bool()
  val runMode = UInt(2.W)
  val cfxCode = UInt(6.W)
  val cfxMask = UInt(64.W)
}

final class DADAOCfxEntryPlan extends Bundle {
  val target = UInt(6.W)
  val cause = UInt(64.W)
  val vector = UInt(64.W)
  val nextMode = UInt(2.W)
  val nextCfxMask = UInt(64.W)
}

final class DADAOCfxIO(
    val params: DADAOParams
) extends Bundle {
  val decoded = Input(new DADAODecodedInstruction)
  val currentIp = Input(UInt(params.addrBits.W))
  val rdValue = Input(UInt(64.W))
  val decoderFault = Input(Bool())
  val fire = Input(Bool())

  val testWrite = Input(new DADAOCfxTestWrite)
  val testRead = Input(new DADAOCfxTestRead)
  val testStatusSet = Input(new DADAOCfxStatusSet)

  val isSystem = Output(Bool())
  val handled = Output(Bool())
  val nextIp = Output(UInt(params.addrBits.W))
  val rdAddr = Output(UInt(6.W))
  val rdWrite = Output(new DADAOTestRegWrite)

  val testReadData = Output(UInt(64.W))
  val testReadValid = Output(Bool())
  val status = Output(new DADAOCfxStatus)
}

final class DADAOCfx(
    val params: DADAOParams = DADAOParams()
) extends Module {
  require(params.addrBits == 64, "D5 CFX requires a 64-bit IP")
  val io = IO(new DADAOCfxIO(params))

  private val ids = DADAODecoderTable.ids
  private val cfx2rdId = ids.indexOf("cfx2rd_crrr_cfx")
  private val cfx2rcId = ids.indexOf("cfx2rc_crrr_cfx")
  private val escapeId = ids.indexOf("escape_ciii_cfx")
  private val trapId = ids.indexOf("trap_ciii_cfx")

  private val isCfx2rd = io.decoded.id === cfx2rdId.U
  private val isCfx2rc = io.decoded.id === cfx2rcId.U
  private val isEscape = io.decoded.id === escapeId.U
  private val isTrap = io.decoded.id === trapId.U
  io.isSystem := isCfx2rd || isCfx2rc || isEscape || isTrap

  private val profileCodes = Seq(
    DADAOCfxCode.Umom,
    DADAOCfxCode.Jmon,
    DADAOCfxCode.Smon,
    DADAOCfxCode.Hmon,
    DADAOCfxCode.Power
  )
  private val profileCount = profileCodes.size
  private val modeCount = 4
  private val modeRows = profileCount * modeCount

  private val defaultSyncMask =
    BigInt("fffffffffffffff7", 16)
  private val hmonSyncMask =
    BigInt("7ffffffffffffff7", 16)
  private val allOnes = BigInt("ffffffffffffffff", 16)
  private val allZeros = BigInt(0)

  private def syncMask(code: Int): BigInt =
    if (code == DADAOCfxCode.Hmon) hmonSyncMask else defaultSyncMask

  private def switchMode(mode: Int): Int =
    if (mode == DADAORunMode.Hypv) DADAORunMode.Hypv
    else DADAORunMode.Supv

  private def resetVector(code: Int, mode: Int): BigInt = {
    if (mode != DADAORunMode.Hypv) {
      allZeros
    } else {
      val value =
        (BigInt(code) << 42) + BigInt("3ffffff0000", 16)
      value & ((BigInt(1) << 48) - 1)
    }
  }

  private val cfxTrap = RegInit(
    VecInit(
      profileCodes.flatMap(code =>
        Seq.fill(modeCount)(syncMask(code).U(64.W))
      )
    )
  )
  private val cfxMem = RegInit(
    VecInit(
      profileCodes.flatMap(code =>
        Seq.fill(modeCount)(syncMask(code).U(64.W))
      )
    )
  )
  private val cfxReg = RegInit(
    VecInit(
      profileCodes.flatMap(code =>
        Seq.fill(modeCount)(syncMask(code).U(64.W))
      )
    )
  )
  private val cfxExe = RegInit(
    VecInit(
      profileCodes.flatMap(code =>
        Seq.fill(modeCount)(syncMask(code).U(64.W))
      )
    )
  )
  private val cfxIntrMask = RegInit(
    VecInit(
      Seq.fill(modeRows)(allOnes.U(64.W))
    )
  )
  private val cfxSwitchMode = RegInit(
    VecInit(
      profileCodes.flatMap(_ =>
        (0 until modeCount).map(mode =>
          switchMode(mode).U(2.W)
        )
      )
    )
  )
  private val cfxSwitchMask = RegInit(
    VecInit(
      Seq.fill(modeRows)(allOnes.U(64.W))
    )
  )
  private val cfxExcpVector = RegInit(
    VecInit(
      profileCodes.flatMap(code =>
        (0 until modeCount).map(mode =>
          resetVector(code, mode).U(64.W)
        )
      )
    )
  )
  private val cfxExcpCauseMask = RegInit(
    VecInit(
      Seq.fill(modeRows)(allOnes.U(64.W))
    )
  )
  private val cfxCgRegDeleg = RegInit(
    VecInit(
      Seq.fill(modeRows)(allOnes.U(64.W))
    )
  )

  private val cfxGlobalIntrMask = RegInit(
    VecInit(
      profileCodes.map { code =>
        (if (code < 4) allOnes else allZeros).U(64.W)
      }
    )
  )
  private val cfxSavedGlobalIntrMask = RegInit(
    VecInit(Seq.fill(profileCount)(allZeros.U(64.W)))
  )
  private val cfxSavedGlobalMonitor =
    RegInit(VecInit(Seq.fill(profileCount)(0.U(2.W))))
  private val cfxSavedGlobalValid =
    RegInit(VecInit(Seq.fill(profileCount)(false.B)))

  private val cfxPrevRunMode =
    RegInit(VecInit(Seq.fill(profileCount)(0.U(2.W))))
  private val cfxPrevCfxMask =
    RegInit(VecInit(Seq.fill(profileCount)(0.U(64.W))))
  private val cfxCauseId =
    RegInit(VecInit(Seq.fill(profileCount)(0.U(64.W))))
  private val cfxCauseIp =
    RegInit(VecInit(Seq.fill(profileCount)(0.U(64.W))))
  private val cfxCauseInfo =
    RegInit(VecInit(Seq.fill(profileCount)(0.U(64.W))))
  private val cfxPending =
    RegInit(VecInit(Seq.fill(profileCount)(0.U(64.W))))

  private val cfxTrapNum =
    RegInit(VecInit(Seq.fill(profileCount)(0.U(64.W))))
  private val cfxSyncNum =
    RegInit(VecInit(Seq.fill(profileCount)(0.U(64.W))))
  private val cfxAsyncNum =
    RegInit(VecInit(Seq.fill(profileCount)(0.U(64.W))))
  private val cfxEscapeNum =
    RegInit(VecInit(Seq.fill(profileCount)(0.U(64.W))))
  private val cfxScratch = RegInit(
    VecInit(
      Seq.fill(profileCount)(
        VecInit(Seq.fill(4)(0.U(64.W)))
      )
    )
  )

  private val innerRunMode =
    RegInit(DADAORunMode.Hypv.U(2.W))
  private val innerCfxCode =
    RegInit(DADAOCfxCode.Power.U(6.W))
  private val innerCfxMask =
    RegInit(allOnes.U(64.W))

  private def supported(code: UInt): Bool =
    code === DADAOCfxCode.Umom.U ||
      code === DADAOCfxCode.Jmon.U ||
      code === DADAOCfxCode.Smon.U ||
      code === DADAOCfxCode.Hmon.U ||
      code === DADAOCfxCode.Power.U

  private def reserved(code: UInt): Bool =
    (code >= 6.U && code <= 14.U) ||
      (code >= 19.U && code <= 61.U)

  private def profileIndex(code: UInt): UInt =
    MuxLookup(code, 4.U(3.W))(
      Seq(
        DADAOCfxCode.Umom.U -> 0.U,
        DADAOCfxCode.Jmon.U -> 1.U,
        DADAOCfxCode.Smon.U -> 2.U,
        DADAOCfxCode.Hmon.U -> 3.U,
        DADAOCfxCode.Power.U -> 4.U
      )
    )

  private def modeIndex(code: UInt, mode: UInt): UInt =
    Cat(profileIndex(code), mode(1, 0))

  private def nonmaskableMask(code: UInt): UInt = {
    val monitorMask =
      DADAOCfxCause.Trap |
        DADAOCfxCause.Mem |
        DADAOCfxCause.Reg |
        DADAOCfxCause.Esc |
        DADAOCfxCause.Perm |
        DADAOCfxCause.Illi |
        (BigInt(1) << 9) |
        (BigInt(1) << 10) |
        (BigInt(1) << 11) |
        (BigInt(1) << 12) |
        (BigInt(1) << 13)
    val powerMask =
      DADAOCfxCause.Trap |
        DADAOCfxCause.Mem |
        DADAOCfxCause.Reg |
        DADAOCfxCause.Esc |
        DADAOCfxCause.Illi |
        (BigInt(1) << 9) |
        (BigInt(1) << 10)
    Mux(
      code < 4.U,
      monitorMask.U(64.W),
      powerMask.U(64.W)
    )
  }

  private def readRegister(
      code: UInt,
      cg: UInt,
      rc: UInt
  ): (Bool, UInt) = {
    val valid = WireDefault(false.B)
    val data = WireDefault(0.U(64.W))
    val row = modeIndex(code, cg)
    val index = profileIndex(code)

    when(supported(code)) {
      when(cg < 4.U) {
        when(rc === 0.U) {
          valid := true.B
          data := cfxTrap(row)
        }.elsewhen(rc === 1.U) {
          valid := true.B
          data := cfxMem(row)
        }.elsewhen(rc === 2.U) {
          valid := true.B
          data := cfxReg(row)
        }.elsewhen(rc === 3.U) {
          valid := true.B
          data := cfxExe(row)
        }.elsewhen(rc === 4.U) {
          valid := true.B
          data := cfxIntrMask(row)
        }.elsewhen(rc === 8.U) {
          valid := true.B
          data := Cat(0.U(62.W), cfxSwitchMode(row))
        }.elsewhen(rc === 9.U) {
          valid := true.B
          data := cfxSwitchMask(row)
        }.elsewhen(rc === 10.U) {
          valid := true.B
          data := cfxExcpVector(row)
        }.elsewhen(rc === 11.U) {
          valid := true.B
          data := cfxExcpCauseMask(row)
        }.elsewhen(cg === 3.U && rc === 12.U) {
          valid := true.B
          data := cfxCgRegDeleg(row)
        }
      }.elsewhen(cg === 4.U) {
        when(rc === 0.U) {
          valid := true.B
          data := code
        }.elsewhen(rc === 1.U) {
          valid := true.B
          data := BigInt("10000", 16).U(64.W)
        }.elsewhen(rc === 2.U) {
          valid := true.B
          data := cfxTrapNum(index)
        }.elsewhen(rc === 3.U) {
          valid := true.B
          data := cfxSyncNum(index)
        }.elsewhen(rc === 4.U) {
          valid := true.B
          data := cfxAsyncNum(index)
        }.elsewhen(rc === 5.U) {
          valid := true.B
          data := cfxEscapeNum(index)
        }.elsewhen(rc === 6.U) {
          valid := true.B
          data := 4.U
        }
      }.elsewhen(cg === 5.U) {
        when(rc === 0.U) {
          valid := true.B
          data := Cat(0.U(62.W), cfxPrevRunMode(index))
        }.elsewhen(rc === 1.U) {
          valid := true.B
          data := cfxPrevCfxMask(index)
        }.elsewhen(rc === 2.U) {
          valid := true.B
          data := cfxCauseId(index)
        }.elsewhen(rc === 3.U) {
          valid := true.B
          data := cfxCauseIp(index)
        }.elsewhen(rc === 4.U) {
          valid := true.B
          data := cfxCauseInfo(index)
        }.elsewhen(rc === 5.U) {
          valid := true.B
          data := cfxPending(index)
        }.elsewhen(rc === 63.U) {
          valid := true.B
          data := nonmaskableMask(code)
        }
      }.elsewhen(cg === 6.U) {
        when(rc < 4.U) {
          valid := true.B
          data := cfxScratch(index)(rc(1, 0))
        }
      }.elsewhen(cg === 8.U) {
        when(code < 4.U && rc === 1.U) {
          valid := true.B
          data := cfxGlobalIntrMask(index)
        }
      }
    }
    (valid, data)
  }

  private def writeRegister(
      enable: Bool,
      code: UInt,
      cg: UInt,
      rc: UInt,
      data: UInt
  ): Bool = {
    val accepted = WireDefault(false.B)
    val row = modeIndex(code, cg)
    val index = profileIndex(code)

    when(enable && supported(code)) {
      when(cg < 4.U) {
        when(rc === 0.U) {
          cfxTrap(row) := data
          accepted := true.B
        }.elsewhen(rc === 1.U) {
          cfxMem(row) := data
          accepted := true.B
        }.elsewhen(rc === 2.U) {
          cfxReg(row) := data
          accepted := true.B
        }.elsewhen(rc === 3.U) {
          cfxExe(row) := data
          accepted := true.B
        }.elsewhen(rc === 4.U) {
          cfxIntrMask(row) := data
          accepted := true.B
        }.elsewhen(rc === 8.U) {
          cfxSwitchMode(row) := data(1, 0)
          accepted := true.B
        }.elsewhen(rc === 9.U) {
          cfxSwitchMask(row) := data
          accepted := true.B
        }.elsewhen(rc === 10.U) {
          cfxExcpVector(row) := data
          accepted := true.B
        }.elsewhen(rc === 11.U) {
          cfxExcpCauseMask(row) := data
          accepted := true.B
        }.elsewhen(cg === 3.U && rc === 12.U) {
          cfxCgRegDeleg(row) := data | (1.U(64.W) << 3)
          accepted := true.B
        }
      }.elsewhen(cg === 5.U) {
        when(rc === 0.U) {
          cfxPrevRunMode(index) := data(1, 0)
          accepted := true.B
        }.elsewhen(rc === 1.U) {
          cfxPrevCfxMask(index) := data
          accepted := true.B
        }.elsewhen(rc === 3.U) {
          cfxCauseIp(index) := data
          accepted := true.B
        }.elsewhen(rc === 5.U) {
          cfxPending(index) := data
          accepted := true.B
        }
      }.elsewhen(cg === 6.U) {
        when(rc < 4.U) {
          cfxScratch(index)(rc(1, 0)) := data
          accepted := true.B
        }
      }.elsewhen(cg === 8.U) {
        when(code < 4.U && rc === 1.U) {
          cfxGlobalIntrMask(index) := data
          accepted := true.B
        }
      }
    }
    accepted
  }

  private def registerWritable(
      code: UInt,
      cg: UInt,
      rc: UInt
  ): Bool = {
    val writable = WireDefault(false.B)
    when(supported(code)) {
      when(cg < 4.U) {
        writable :=
          rc <= 4.U ||
            (rc >= 8.U && rc <= 11.U) ||
            (cg === 3.U && rc === 12.U)
      }.elsewhen(cg === 5.U) {
        writable :=
          rc === 0.U ||
            rc === 1.U ||
            rc === 3.U ||
            rc === 5.U
      }.elsewhen(cg === 6.U) {
        writable := rc < 4.U
      }.elsewhen(cg === 8.U) {
        writable := code < 4.U && rc === 1.U
      }
    }
    writable
  }

  private val instruction =
    Cat(0.U(32.W), io.decoded.word)
  private val isSemihostingTrap =
    io.decoded.word(17, 8) === 0x3ff.U
  private val targetCfx = io.decoded.word(23, 18)
  private val cg = io.decoded.word(17, 12)
  private val rc = io.decoded.word(11, 6)
  private val rdAddr = io.decoded.word(5, 0)
  private val targetIndex = profileIndex(targetCfx)
  private val currentIndex = profileIndex(innerCfxCode)
  private val currentModeMonitor =
    Cat(0.U(4.W), innerRunMode)

  private def bitSet(mask: UInt, index: UInt): Bool =
    ((mask >> index) & 1.U) =/= 0.U

  private val trapPermissionDenied =
    targetCfx =/= innerCfxCode &&
      bitSet(
        cfxTrap(modeIndex(targetCfx, innerRunMode)),
        innerCfxCode
      )
  private val regPermissionDenied =
    targetCfx =/= innerCfxCode &&
      bitSet(
        cfxReg(modeIndex(targetCfx, innerRunMode)),
        innerCfxCode
      )
  private val supvDelegationDenied =
    innerRunMode === DADAORunMode.Supv.U &&
      bitSet(
        cfxCgRegDeleg(
          Cat(targetIndex, DADAORunMode.Hypv.U(2.W))
        ),
        cg
      )

  private def entryPlan(
      target: UInt,
      cause: UInt,
      causeInfo: UInt
  ): DADAOCfxEntryPlan = {
    val plan = Wire(new DADAOCfxEntryPlan)
    val row = modeIndex(target, innerRunMode)
    plan.target := target
    plan.cause := cause
    plan.vector := cfxExcpVector(row)
    plan.nextMode := cfxSwitchMode(row)
    plan.nextCfxMask := cfxSwitchMask(row)
    plan
  }

  private val entry = Wire(new DADAOCfxEntryPlan)
  entry := 0.U.asTypeOf(new DADAOCfxEntryPlan)
  private val enter = WireDefault(false.B)
  private val success = WireDefault(false.B)
  private val nextIp = WireDefault(io.currentIp)
  private val rdWriteValid = WireDefault(false.B)
  private val rdWriteData = WireDefault(0.U(64.W))

  private val readValid = WireDefault(false.B)
  private val readData = WireDefault(0.U(64.W))
  private val writeValid = WireDefault(false.B)

  when(isCfx2rd) {
    val result = readRegister(targetCfx, cg, rc)
    readValid := result._1
    readData := result._2
  }
  when(isCfx2rc) {
    writeValid := registerWritable(targetCfx, cg, rc)
  }

  when(io.fire) {
    when(io.decoderFault) {
      entry := entryPlan(
        currentModeMonitor,
        DADAOCfxCause.Illi.U,
        instruction
      )
      enter := true.B
    }.elsewhen(isTrap) {
      when(isSemihostingTrap) {
        entry := entryPlan(
          currentModeMonitor,
          DADAOCfxCause.Illi.U,
          instruction
        )
        enter := true.B
      }.elsewhen(reserved(targetCfx)) {
        entry := entryPlan(
          currentModeMonitor,
          DADAOCfxCause.Illi.U,
          instruction
        )
        enter := true.B
      }.elsewhen(!supported(targetCfx)) {
        entry := entryPlan(
          currentModeMonitor,
          DADAOCfxCause.Reg.U,
          instruction
        )
        enter := true.B
      }.elsewhen(trapPermissionDenied) {
        entry := entryPlan(
          currentModeMonitor,
          DADAOCfxCause.Perm.U,
          instruction
        )
        enter := true.B
      }.otherwise {
        entry := entryPlan(
          targetCfx,
          DADAOCfxCause.Trap.U,
          instruction
        )
        enter := true.B
      }
    }.elsewhen(isCfx2rd || isCfx2rc) {
      when(reserved(targetCfx)) {
        entry := entryPlan(
          currentModeMonitor,
          DADAOCfxCause.Illi.U,
          instruction
        )
        enter := true.B
      }.elsewhen(!supported(targetCfx)) {
        entry := entryPlan(
          currentModeMonitor,
          DADAOCfxCause.Reg.U,
          instruction
        )
        enter := true.B
      }.elsewhen(regPermissionDenied || supvDelegationDenied) {
        entry := entryPlan(
          currentModeMonitor,
          DADAOCfxCause.Perm.U,
          instruction
        )
        enter := true.B
      }.elsewhen(isCfx2rd && !readValid) {
        entry := entryPlan(
          currentModeMonitor,
          DADAOCfxCause.Reg.U,
          instruction
        )
        enter := true.B
      }.elsewhen(isCfx2rc && !writeValid) {
        entry := entryPlan(
          currentModeMonitor,
          DADAOCfxCause.Reg.U,
          instruction
        )
        enter := true.B
      }.otherwise {
        success := true.B
        nextIp := io.currentIp + 4.U
        when(isCfx2rd && rdAddr =/= 0.U) {
          rdWriteValid := true.B
          rdWriteData := readData
        }
      }
    }.elsewhen(isEscape) {
      when(
        reserved(targetCfx)
      ) {
        entry := entryPlan(
          currentModeMonitor,
          DADAOCfxCause.Illi.U,
          instruction
        )
        enter := true.B
      }.elsewhen(
        !supported(innerCfxCode) ||
          targetCfx =/= innerCfxCode ||
          cfxCauseId(currentIndex) === 0.U
      ) {
        entry := entryPlan(
          Mux(
            supported(innerCfxCode),
            innerCfxCode,
            currentModeMonitor
          ),
          DADAOCfxCause.Esc.U,
          instruction
        )
        enter := true.B
      }.otherwise {
        success := true.B
        nextIp :=
          cfxCauseIp(currentIndex) +
            (io.decoded.word(0) << 2)
      }
    }
  }

  io.handled := io.fire && io.isSystem
  io.nextIp := Mux(enter, entry.vector, nextIp)
  io.rdAddr := rdAddr
  io.rdWrite.valid := rdWriteValid
  io.rdWrite.bank := DADAORegBank.Rd.U
  io.rdWrite.addr := rdAddr
  io.rdWrite.data := rdWriteData
  io.status.runMode := innerRunMode
  io.status.cfxCode := innerCfxCode
  io.status.cfxMask := innerCfxMask

  private val testReadResult = readRegister(
    io.testRead.cfxha,
    io.testRead.cg,
    io.testRead.rc
  )
  io.testReadData := testReadResult._2
  io.testReadValid := testReadResult._1

  writeRegister(
    io.fire && isCfx2rc && success,
    targetCfx,
    cg,
    rc,
    io.rdValue
  )
  writeRegister(
    io.testWrite.valid,
    io.testWrite.cfxha,
    io.testWrite.cg,
    io.testWrite.rc,
    io.testWrite.data
  )

  when(io.testStatusSet.valid) {
    innerRunMode := io.testStatusSet.runMode
    innerCfxCode := io.testStatusSet.cfxCode
    innerCfxMask := io.testStatusSet.cfxMask
  }.elsewhen(enter) {
    val targetIdx = profileIndex(entry.target)
    val monitor = innerRunMode
    cfxPrevRunMode(targetIdx) := innerRunMode
    cfxPrevCfxMask(targetIdx) := innerCfxMask
    cfxCauseId(targetIdx) := entry.cause
    cfxCauseIp(targetIdx) := io.currentIp
    cfxCauseInfo(targetIdx) := instruction
    cfxSavedGlobalValid(targetIdx) :=
      entry.cause === DADAOCfxCause.Trap.U
    when(entry.cause === DADAOCfxCause.Trap.U) {
      cfxTrapNum(targetIdx) := cfxTrapNum(targetIdx) + 1.U
      cfxSavedGlobalMonitor(targetIdx) := monitor
      cfxSavedGlobalIntrMask(targetIdx) :=
        cfxGlobalIntrMask(Cat(0.U(1.W), monitor))
      cfxGlobalIntrMask(Cat(0.U(1.W), monitor)) :=
        allOnes.U(64.W)
    }.otherwise {
      cfxSyncNum(targetIdx) := cfxSyncNum(targetIdx) + 1.U
    }
    innerRunMode := entry.nextMode
    innerCfxMask := entry.nextCfxMask
    innerCfxCode := entry.target
  }.elsewhen(success && isEscape) {
    when(cfxSavedGlobalValid(currentIndex)) {
      val savedMonitor =
        cfxSavedGlobalMonitor(currentIndex)
      cfxGlobalIntrMask(Cat(0.U(1.W), savedMonitor)) :=
        cfxSavedGlobalIntrMask(currentIndex)
    }
    cfxSavedGlobalValid(currentIndex) := false.B
    innerRunMode := cfxPrevRunMode(currentIndex)
    innerCfxMask := cfxPrevCfxMask(currentIndex)
    cfxEscapeNum(currentIndex) :=
      cfxEscapeNum(currentIndex) + 1.U
  }
}
