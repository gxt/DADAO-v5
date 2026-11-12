package dadao

import chisel3._
import chisel3.util.{Cat, Fill}

final class DADAOCoreIO(
    val params: DADAOParams,
    val testMode: Boolean
) extends Bundle {
  val mem = new DADAOMemPort(params.addrBits, params.dataBits)
  val pc = Output(UInt(params.addrBits.W))

  val pcInitValid = Option.when(testMode)(Input(Bool()))
  val pcInit =
    Option.when(testMode)(Input(UInt(params.addrBits.W)))
  val debugPc =
    Option.when(testMode)(Output(UInt(params.addrBits.W)))
  val debugDecodedValid =
    Option.when(testMode)(Output(Bool()))
  val debugWord =
    Option.when(testMode)(Output(UInt(32.W)))
  val debugId =
    Option.when(testMode)(Output(UInt(9.W)))
  val debugFormat =
    Option.when(testMode)(Output(UInt(4.W)))
  val debugScope =
    Option.when(testMode)(Output(UInt(2.W)))
  val debugNoop =
    Option.when(testMode)(Output(Bool()))
  val debugFault =
    Option.when(testMode)(Output(Bool()))
  val debugFaultCode =
    Option.when(testMode)(Output(UInt(8.W)))
  val debugFaultReason =
    Option.when(testMode)(Output(UInt(3.W)))
  val debugMemOwner =
    Option.when(testMode)(Output(UInt(2.W)))
  val debugRasDone =
    Option.when(testMode)(Output(Bool()))
  val debugRasFault =
    Option.when(testMode)(Output(Bool()))
  val debugRasMemReqValid =
    Option.when(testMode)(Output(Bool()))
  val debugRasState =
    Option.when(testMode)(Output(UInt(2.W)))
  val testCfxWrite =
    Option.when(testMode)(Input(new DADAOCfxTestWrite))
  val testCfxStatusSet =
    Option.when(testMode)(Input(new DADAOCfxStatusSet))
  val debugCfxRead =
    Option.when(testMode)(Input(new DADAOCfxTestRead))
  val debugCfxReadData =
    Option.when(testMode)(Output(UInt(64.W)))
  val debugCfxReadValid =
    Option.when(testMode)(Output(Bool()))
  val debugCfxStatus =
    Option.when(testMode)(Output(new DADAOCfxStatus))
  val testRegWrite =
    Option.when(testMode)(Input(new DADAOTestRegWrite))
  val debugRegBank =
    Option.when(testMode)(Input(UInt(2.W)))
  val debugRegAddr =
    Option.when(testMode)(Input(UInt(6.W)))
  val debugRegData =
    Option.when(testMode)(Output(UInt(64.W)))
  val debugDataRequestAddr =
    Option.when(testMode)(Output(UInt(params.addrBits.W)))
  val debugDataRequestWrite =
    Option.when(testMode)(Output(Bool()))
  val debugDataRequestWdata =
    Option.when(testMode)(Output(UInt(64.W)))
  val debugDataRequestWstrb =
    Option.when(testMode)(Output(UInt(8.W)))
  val debugDataResponseData =
    Option.when(testMode)(Output(UInt(64.W)))
  val debugLoadWrite =
    Option.when(testMode)(Output(Bool()))
  val debugLoadWriteData =
    Option.when(testMode)(Output(UInt(64.W)))
}

final class DADAOCore(
    val params: DADAOParams = DADAOParams(),
    val testMode: Boolean = false
) extends Module {
  val io = IO(new DADAOCoreIO(params, testMode))
  require(
    params.addrBits == 64,
    "DADAO rb0/ip requires a 64-bit pcReg; fetch uses pcReg[47:0]"
  )

  private val memOwner = RegInit(DADAOMemOwner.Idle.U(2.W))
  private val dataRequestAccepted = RegInit(false.B)
  private val halted = RegInit(false.B)
  private val pcReg =
    RegInit(params.resetVector.U(params.addrBits.W))
  private val fetchIp = pcReg(47, 0)
  private val fetchAddress =
    Cat(0.U((params.addrBits - 48).W), fetchIp)
  private val nextRb0 = Wire(UInt(params.addrBits.W))
  nextRb0 := pcReg + 4.U
  private val requestBits =
    RegInit(0.U.asTypeOf(new DADAOMemReq(params.addrBits, params.dataBits)))
  private val dataRequestBits =
    RegInit(0.U.asTypeOf(new DADAOMemReq(params.addrBits, params.dataBits)))
  private val blockActive = RegInit(false.B)
  private val blockPrecheck = RegInit(false.B)
  private val blockEmit = RegInit(false.B)
  private val blockIndex = RegInit(0.U(6.W))
  private val blockStartAddr =
    RegInit(0.U(params.addrBits.W))
  private val blockSawUnmapped = RegInit(false.B)
  private val blockSawMalign = RegInit(false.B)
  private val blockSawIlli = RegInit(false.B)
  private val loadBuffer =
    RegInit(VecInit(Seq.fill(63)(0.U(64.W))))

  private val decodedValidReg = RegInit(false.B)
  private val decodedWordReg = RegInit(0.U(32.W))
  private val decodedIdReg = RegInit(0.U(9.W))
  private val decodedFormatReg = RegInit(0.U(4.W))
  private val decodedScopeReg = RegInit(0.U(2.W))
  private val decodedNoopReg = RegInit(false.B)
  private val faultReg = RegInit(false.B)
  private val faultCodeReg = RegInit(DADAOFaultCode.None.U(8.W))
  private val faultReasonReg = RegInit(DADAODebugFaultReason.None.U(3.W))

  private val decoder = Module(new DADAODecoder)
  decoder.io.word := Mux(
    memOwner === DADAOMemOwner.Fetch.U && io.mem.resp.valid,
    io.mem.resp.bits.rdata(31, 0),
    decodedWordReg
  )
  private val regFile = Module(new DADAORegFile(params))
  private val intExec = Module(new DADAOIntExec(params, testMode))
  private val loadExec = Module(new DADAOLoadExec(params))
  private val storeExec = Module(new DADAOStoreExec(params))
  private val blockExec = Module(new DADAOBlockMemExec(params))
  private val controlExec = Module(new DADAOControlExec(params))
  private val cfx = Module(new DADAOCfx(params))
  private val fetchAccessCheck = Module(new DADAOAccessCheck(params))
  private val dataAccessCheck = Module(new DADAOAccessCheck(params))
  private val blockAccessCheck = Module(new DADAOAccessCheck(params))

  private val fetchResponseFire =
    memOwner === DADAOMemOwner.Fetch.U &&
      io.mem.resp.valid &&
      io.mem.resp.ready &&
      !io.mem.resp.bits.fault

  intExec.io.regFile <> regFile.io
  intExec.io.pc := pcReg
  intExec.io.decoded := decoder.io.decoded
  intExec.io.control := decoder.io.control
  intExec.io.commit :=
    fetchResponseFire &&
      !decoder.io.control.fault &&
      !loadExec.io.isLoad &&
      !storeExec.io.isStore &&
      !blockExec.io.isBlock &&
      !controlExec.io.isControl &&
      !cfx.io.isSystem

  loadExec.io.decoded := decoder.io.decoded
  loadExec.io.baseValue := intExec.io.extRead0Data
  loadExec.io.responseData := io.mem.resp.bits.rdata
  loadExec.io.responseValid :=
    memOwner === DADAOMemOwner.Data.U &&
      io.mem.resp.valid &&
      io.mem.resp.ready
  loadExec.io.responseFault :=
    memOwner === DADAOMemOwner.Data.U &&
      io.mem.resp.valid &&
      io.mem.resp.ready &&
      io.mem.resp.bits.fault

  storeExec.io.decoded := decoder.io.decoded
  storeExec.io.baseValue := intExec.io.extRead0Data
  storeExec.io.sourceValue := intExec.io.extRead1Data

  private val blockElementOffset =
    (Cat(0.U(58.W), blockIndex) << blockExec.io.requestSize)
  private val blockElementAddr =
    blockStartAddr + blockElementOffset
  private val blockLast =
    blockIndex + 1.U === blockExec.io.count

  blockExec.io.decoded := decoder.io.decoded
  blockExec.io.baseValue := intExec.io.extRead0Data
  blockExec.io.offsetValue := intExec.io.extRead1Data
  blockExec.io.address := blockElementAddr
  blockExec.io.sourceValue := intExec.io.extRead1Data
  blockExec.io.responseValue := io.mem.resp.bits.rdata

  controlExec.io.decoded := decoder.io.decoded
  controlExec.io.currentRb0 := pcReg
  controlExec.io.read0Value := intExec.io.extRead0Data
  controlExec.io.read1Value := intExec.io.extRead1Data
  controlExec.io.poppedReturnAddress :=
    regFile.rasControl.resp.popAddress
  cfx.io.decoded := decoder.io.decoded
  cfx.io.currentIp := pcReg
  cfx.io.rdValue := intExec.io.extRead1Data
  cfx.io.decoderFault := decoder.io.control.fault
  cfx.io.fire := fetchResponseFire && cfx.io.isSystem
  if (testMode) {
    cfx.io.testWrite := io.testCfxWrite.get
    cfx.io.testRead := io.debugCfxRead.get
    cfx.io.testStatusSet := io.testCfxStatusSet.get
  } else {
    cfx.io.testWrite := 0.U.asTypeOf(new DADAOCfxTestWrite)
    cfx.io.testRead := 0.U.asTypeOf(new DADAOCfxTestRead)
    cfx.io.testStatusSet := 0.U.asTypeOf(new DADAOCfxStatusSet)
  }
  private val controlFetchCandidate =
    fetchResponseFire &&
      !decoder.io.control.fault
  private val rasMemoryResponse =
    memOwner === DADAOMemOwner.Ras.U &&
      io.mem.resp.valid
  private val controlFetchCommit =
    controlFetchCandidate &&
      controlExec.io.isControl &&
      (!(controlExec.io.isCall || controlExec.io.isRet) ||
        (regFile.rasControl.resp.done &&
          !regFile.rasControl.resp.fault))
  private val controlMemoryCommit =
    rasMemoryResponse &&
      regFile.rasControl.resp.done &&
      !regFile.rasControl.resp.fault
  private val controlCommit =
    controlFetchCommit || controlMemoryCommit
  private val rasPushRequest =
    controlFetchCandidate && controlExec.io.isCall
  private val rasPopRequest =
    controlFetchCandidate && controlExec.io.isRet
  regFile.rasControl.req.push := rasPushRequest
  regFile.rasControl.req.pushAddress :=
    controlExec.io.callReturnAddress
  regFile.rasControl.req.pop := rasPopRequest
  private val rasMemRequest =
    !halted &&
      memOwner === DADAOMemOwner.Ras.U &&
      regFile.rasControl.resp.memReqValid
  private val rasMemAccepted =
    rasMemRequest && io.mem.req.ready
  regFile.rasControl.memReqAccepted := rasMemAccepted
  regFile.rasControl.memResp.valid := rasMemoryResponse
  regFile.rasControl.memResp.data := io.mem.resp.bits.rdata
  regFile.rasControl.memResp.fault := io.mem.resp.bits.fault
  regFile.rasControl.memResp.faultCode :=
    io.mem.resp.bits.faultCode
  when(controlExec.io.isControl) {
    nextRb0 := controlExec.io.nextRb0
  }

  fetchAccessCheck.io.addr := fetchAddress
  fetchAccessCheck.io.write := false.B
  fetchAccessCheck.io.size := DADAOMemSize.Tetra.U
  fetchAccessCheck.io.kind := DADAOMemKind.Fetch.U

  dataAccessCheck.io.addr :=
    Mux(
      storeExec.io.isStore,
      storeExec.io.requestAddr,
      loadExec.io.requestAddr
    )
  dataAccessCheck.io.write := storeExec.io.isStore
  dataAccessCheck.io.size :=
    Mux(
      storeExec.io.isStore,
      storeExec.io.requestSize,
      loadExec.io.requestSize
    )
  dataAccessCheck.io.kind := DADAOMemKind.Data.U

  blockAccessCheck.io.addr := blockElementAddr
  blockAccessCheck.io.write := blockExec.io.isStore
  blockAccessCheck.io.size := blockExec.io.requestSize
  blockAccessCheck.io.kind := DADAOMemKind.Data.U

  private val memoryRead0Addr =
    Mux(
      blockExec.io.isBlock,
      blockExec.io.baseRegAddr,
      Mux(
        storeExec.io.isStore,
        storeExec.io.baseRegAddr,
        loadExec.io.baseRegAddr
      )
    )
  intExec.io.extRead0Bank :=
    Mux(
      controlExec.io.isControl,
      controlExec.io.read0Bank,
      DADAORegBank.Rb.U
    )
  intExec.io.extRead0Addr :=
    Mux(
      controlExec.io.isControl,
      controlExec.io.read0Addr,
      memoryRead0Addr
    )
  private val blockReadsOffset =
    blockExec.io.isBlock && !blockActive
  private val blockReadsSource =
    blockActive && blockExec.io.isStore
  private val blockSourceIndex =
    blockExec.io.startRegAddr + blockIndex
  private val memoryRead1Bank =
    Mux(
      blockReadsOffset,
      DADAORegBank.Rd.U,
      Mux(
        blockReadsSource,
        blockExec.io.targetBank,
        storeExec.io.sourceBank
      )
    )
  private val memoryRead1Addr =
    Mux(
      blockReadsOffset,
      blockExec.io.offsetRegAddr,
      Mux(
        blockReadsSource,
        blockSourceIndex,
        storeExec.io.sourceRegAddr
      )
    )
  intExec.io.extRead1Bank :=
    Mux(
      cfx.io.isSystem,
      DADAORegBank.Rd.U,
      Mux(
        controlExec.io.isControl,
        controlExec.io.read1Bank,
        memoryRead1Bank
      )
    )
  intExec.io.extRead1Addr :=
    Mux(
      cfx.io.isSystem,
      cfx.io.rdAddr,
      Mux(
        controlExec.io.isControl,
        controlExec.io.read1Addr,
        memoryRead1Addr
      )
    )
  private val retWrite = Wire(new DADAOTestRegWrite)
  retWrite.valid :=
    controlCommit &&
      controlExec.io.isRet &&
      controlExec.io.retRdWrite
  retWrite.bank := DADAORegBank.Rd.U
  retWrite.addr := controlExec.io.retRdAddr
  retWrite.data := controlExec.io.retRdValue
  when(cfx.io.rdWrite.valid) {
    intExec.io.extWrite := cfx.io.rdWrite
  }.elsewhen(retWrite.valid) {
    intExec.io.extWrite := retWrite
  }.otherwise {
    intExec.io.extWrite := loadExec.io.write
  }

  private val blockWrite = Wire(new DADAOBlockRegWrite)
  blockWrite := 0.U.asTypeOf(new DADAOBlockRegWrite)
  blockWrite.data := VecInit(
    (0 until 63).map { index =>
      Mux(
        blockIndex === index.U,
        blockExec.io.loadValue,
        loadBuffer(index)
      )
    }
  )
  when(
    blockActive &&
      blockExec.io.isLoad &&
      blockLast &&
      memOwner === DADAOMemOwner.Data.U &&
      io.mem.resp.valid &&
      io.mem.resp.ready &&
      !io.mem.resp.bits.fault
  ) {
    blockWrite.valid := true.B
    blockWrite.bank := blockExec.io.targetBank
    blockWrite.start := blockExec.io.startRegAddr
    blockWrite.count := blockExec.io.count
  }
  intExec.io.blockWrite := blockWrite

  private val pcAligned = fetchIp(1, 0) === 0.U
  private val pcInitHold =
    if (testMode) io.pcInitValid.get else false.B
  private val fetchReady =
    !halted &&
      !blockActive &&
      memOwner === DADAOMemOwner.Idle.U &&
      pcAligned &&
      !fetchAccessCheck.io.fault &&
      !pcInitHold
  private val dataRequestPending =
    !halted &&
      memOwner === DADAOMemOwner.Data.U &&
      !dataRequestAccepted

  io.pc := pcReg
  io.mem.req.valid :=
    fetchReady || dataRequestPending || rasMemRequest
  when(rasMemRequest) {
    io.mem.req.bits.addr :=
      regFile.rasControl.resp.memReqAddr
    io.mem.req.bits.write :=
      regFile.rasControl.resp.memReqWrite
    io.mem.req.bits.size := DADAOMemSize.Octa.U
    io.mem.req.bits.wdata :=
      regFile.rasControl.resp.memReqWdata
    io.mem.req.bits.wstrb :=
      Fill(8, regFile.rasControl.resp.memReqWrite)
    io.mem.req.bits.kind := DADAOMemKind.Data.U
  }.elsewhen(dataRequestPending) {
    io.mem.req.bits := dataRequestBits
  }.otherwise {
    io.mem.req.bits.addr :=
      Mux(
        memOwner === DADAOMemOwner.Fetch.U,
        requestBits.addr,
        fetchAddress
      )
    io.mem.req.bits.write := false.B
    io.mem.req.bits.size := DADAOMemSize.Tetra.U
    io.mem.req.bits.wdata := 0.U
    io.mem.req.bits.wstrb := 0.U
    io.mem.req.bits.kind := DADAOMemKind.Fetch.U
  }
  io.mem.resp.ready := !halted

  private def resetCore(pcValue: UInt): Unit = {
    memOwner := DADAOMemOwner.Idle.U
    dataRequestAccepted := false.B
    halted := false.B
    pcReg := pcValue
    requestBits.addr :=
      Cat(0.U((params.addrBits - 48).W), pcValue(47, 0))
    requestBits.write := false.B
    requestBits.size := DADAOMemSize.Tetra.U
    requestBits.wdata := 0.U
    requestBits.wstrb := 0.U
    requestBits.kind := DADAOMemKind.Fetch.U
    dataRequestBits :=
      0.U.asTypeOf(new DADAOMemReq(params.addrBits, params.dataBits))
    blockActive := false.B
    blockPrecheck := false.B
    blockEmit := false.B
    blockIndex := 0.U
    blockStartAddr := 0.U
    blockSawUnmapped := false.B
    blockSawMalign := false.B
    blockSawIlli := false.B
    for (index <- 0 until 63) {
      loadBuffer(index) := 0.U
    }
    decodedValidReg := false.B
    decodedWordReg := 0.U
    decodedIdReg := 0.U
    decodedFormatReg := 0.U
    decodedScopeReg := 0.U
    decodedNoopReg := false.B
    faultReg := false.B
    faultCodeReg := DADAOFaultCode.None.U
    faultReasonReg := DADAODebugFaultReason.None.U
  }

  private def normalCycle(): Unit = {
    when(!halted) {
      when(!pcAligned) {
        halted := true.B
        faultReg := true.B
        faultCodeReg := DADAOFaultCode.Ialign.U
        faultReasonReg := DADAODebugFaultReason.IlliField.U
      }.elsewhen(
        !blockActive &&
          memOwner === DADAOMemOwner.Idle.U &&
          fetchAccessCheck.io.fault
      ) {
        halted := true.B
        faultReg := true.B
        faultCodeReg := fetchAccessCheck.io.faultCode
        faultReasonReg := DADAODebugFaultReason.AccessFault.U
      }.elsewhen(blockActive && blockPrecheck) {
        when(
          blockAccessCheck.io.faultCode ===
            DADAOFaultCode.Unmapped.U
        ) {
          blockSawUnmapped := true.B
        }
        when(
          blockAccessCheck.io.faultCode ===
            DADAOFaultCode.Malign.U
        ) {
          blockSawMalign := true.B
        }
        when(
          blockAccessCheck.io.faultCode ===
            DADAOFaultCode.Illi.U
        ) {
          blockSawIlli := true.B
        }

        when(blockLast) {
          val finalUnmapped =
            blockSawUnmapped ||
              blockAccessCheck.io.faultCode ===
                DADAOFaultCode.Unmapped.U
          val finalMalign =
            blockSawMalign ||
              blockAccessCheck.io.faultCode ===
                DADAOFaultCode.Malign.U
          val finalIlli =
            blockSawIlli ||
              blockAccessCheck.io.faultCode ===
                DADAOFaultCode.Illi.U

          when(finalUnmapped) {
            halted := true.B
            blockActive := false.B
            blockPrecheck := false.B
            faultReg := true.B
            faultCodeReg := DADAOFaultCode.Unmapped.U
            faultReasonReg := DADAODebugFaultReason.AccessFault.U
          }.elsewhen(finalMalign) {
            halted := true.B
            blockActive := false.B
            blockPrecheck := false.B
            faultReg := true.B
            faultCodeReg := DADAOFaultCode.Malign.U
            faultReasonReg := DADAODebugFaultReason.AccessFault.U
          }.elsewhen(finalIlli) {
            halted := true.B
            blockActive := false.B
            blockPrecheck := false.B
            faultReg := true.B
            faultCodeReg := DADAOFaultCode.Illi.U
            faultReasonReg := DADAODebugFaultReason.AccessFault.U
          }.otherwise {
            blockPrecheck := false.B
            blockEmit := true.B
            blockIndex := 0.U
            dataRequestAccepted := false.B
            memOwner := DADAOMemOwner.Idle.U
          }
        }.otherwise {
          blockIndex := blockIndex + 1.U
        }
      }.elsewhen(blockActive && blockEmit) {
        dataRequestBits :=
          0.U.asTypeOf(new DADAOMemReq(params.addrBits, params.dataBits))
        dataRequestBits.addr := blockElementAddr
        dataRequestBits.write := blockExec.io.isStore
        dataRequestBits.size := blockExec.io.requestSize
        dataRequestBits.wdata :=
          Mux(
            blockExec.io.isStore,
            blockExec.io.requestWdata,
            0.U
          )
        dataRequestBits.wstrb :=
          Mux(
            blockExec.io.isStore,
            blockExec.io.requestWstrb,
            0.U
          )
        dataRequestBits.kind := DADAOMemKind.Data.U
        dataRequestAccepted := false.B
        blockEmit := false.B
        memOwner := DADAOMemOwner.Data.U
      }.elsewhen(
        memOwner === DADAOMemOwner.Data.U &&
          !dataRequestAccepted
      ) {
        when(io.mem.req.ready) {
          dataRequestAccepted := true.B
        }
      }.elsewhen(
        memOwner === DADAOMemOwner.Data.U &&
          dataRequestAccepted
      ) {
        when(io.mem.resp.valid) {
          when(io.mem.resp.bits.fault) {
            halted := true.B
            blockActive := false.B
            blockEmit := false.B
            faultReg := true.B
            faultCodeReg := io.mem.resp.bits.faultCode
            faultReasonReg := DADAODebugFaultReason.AccessFault.U
          }.elsewhen(blockActive) {
            when(blockExec.io.isLoad) {
              loadBuffer(blockIndex) := blockExec.io.loadValue
            }
            when(blockLast) {
              blockActive := false.B
              blockPrecheck := false.B
              blockEmit := false.B
              blockIndex := 0.U
              memOwner := DADAOMemOwner.Idle.U
              dataRequestAccepted := false.B
              pcReg := nextRb0
            }.otherwise {
              blockIndex := blockIndex + 1.U
              blockEmit := true.B
              memOwner := DADAOMemOwner.Idle.U
              dataRequestAccepted := false.B
            }
          }.otherwise {
            memOwner := DADAOMemOwner.Idle.U
            dataRequestAccepted := false.B
            pcReg := nextRb0
          }
        }
      }.elsewhen(
        memOwner === DADAOMemOwner.Ras.U &&
          io.mem.resp.valid
      ) {
        when(regFile.rasControl.resp.fault) {
          halted := true.B
          faultReg := true.B
          faultCodeReg := regFile.rasControl.resp.faultCode
          faultReasonReg := Mux(
            regFile.rasControl.resp.faultCode ===
              DADAOFaultCode.Rasuf.U,
            DADAODebugFaultReason.IlliOperand.U,
            DADAODebugFaultReason.AccessFault.U
          )
        }.elsewhen(regFile.rasControl.resp.done) {
          decodedValidReg := true.B
          decodedIdReg := decoder.io.decoded.id
          decodedFormatReg := decoder.io.decoded.format
          decodedScopeReg := decoder.io.control.scope
          decodedNoopReg := false.B
          pcReg := nextRb0
          memOwner := DADAOMemOwner.Idle.U
        }
      }.elsewhen(memOwner === DADAOMemOwner.Idle.U) {
        when(io.mem.req.ready) {
          requestBits := io.mem.req.bits
          memOwner := DADAOMemOwner.Fetch.U
        }
      }.elsewhen(memOwner === DADAOMemOwner.Fetch.U) {
        when(io.mem.resp.valid) {
          memOwner := DADAOMemOwner.Idle.U
          decodedWordReg := io.mem.resp.bits.rdata(31, 0)

          when(io.mem.resp.bits.fault) {
            halted := true.B
            faultReg := true.B
            faultCodeReg := io.mem.resp.bits.faultCode
            faultReasonReg := DADAODebugFaultReason.IlliOperand.U
          }.elsewhen(cfx.io.isSystem) {
            decodedValidReg := true.B
            decodedIdReg := decoder.io.decoded.id
            decodedFormatReg := decoder.io.decoded.format
            decodedScopeReg := decoder.io.control.scope
            decodedNoopReg := false.B
            pcReg := cfx.io.nextIp
          }.elsewhen(decoder.io.control.fault) {
            halted := true.B
            faultReg := true.B
            faultCodeReg := decoder.io.control.faultCode
            faultReasonReg := decoder.io.control.debugFaultReason
            decodedIdReg := decoder.io.decoded.id
            decodedFormatReg := decoder.io.decoded.format
            decodedScopeReg := decoder.io.control.scope
          }.elsewhen(controlExec.io.isControl) {
            when(controlExec.io.isCall || controlExec.io.isRet) {
              when(regFile.rasControl.resp.fault) {
                halted := true.B
                faultReg := true.B
                faultCodeReg := regFile.rasControl.resp.faultCode
                faultReasonReg :=
                  DADAODebugFaultReason.IlliOperand.U
                decodedIdReg := decoder.io.decoded.id
                decodedFormatReg := decoder.io.decoded.format
                decodedScopeReg := decoder.io.control.scope
              }.elsewhen(regFile.rasControl.resp.done) {
                decodedValidReg := true.B
                decodedIdReg := decoder.io.decoded.id
                decodedFormatReg := decoder.io.decoded.format
                decodedScopeReg := decoder.io.control.scope
                decodedNoopReg := false.B
                pcReg := nextRb0
              }.elsewhen(regFile.rasControl.resp.memStart) {
                memOwner := DADAOMemOwner.Ras.U
              }.otherwise {
                halted := true.B
                faultReg := true.B
                faultCodeReg := DADAOFaultCode.Illi.U
                faultReasonReg :=
                  DADAODebugFaultReason.IlliOperand.U
              }
            }.otherwise {
              decodedValidReg := true.B
              decodedIdReg := decoder.io.decoded.id
              decodedFormatReg := decoder.io.decoded.format
              decodedScopeReg := decoder.io.control.scope
              decodedNoopReg := false.B
              pcReg := nextRb0
            }
          }.elsewhen(blockExec.io.isBlock) {
            decodedValidReg := true.B
            decodedIdReg := decoder.io.decoded.id
            decodedFormatReg := decoder.io.decoded.format
            decodedScopeReg := decoder.io.control.scope
            decodedNoopReg := false.B
            blockActive := true.B
            blockPrecheck := true.B
            blockEmit := false.B
            blockIndex := 0.U
            blockStartAddr := blockExec.io.firstAddress
            blockSawUnmapped := false.B
            blockSawMalign := false.B
            blockSawIlli := false.B
            dataRequestAccepted := false.B
            memOwner := DADAOMemOwner.Idle.U
          }.elsewhen(loadExec.io.isLoad) {
            decodedValidReg := true.B
            decodedIdReg := decoder.io.decoded.id
            decodedFormatReg := decoder.io.decoded.format
            decodedScopeReg := decoder.io.control.scope
            decodedNoopReg := false.B
            when(dataAccessCheck.io.fault) {
              halted := true.B
              faultReg := true.B
              faultCodeReg := dataAccessCheck.io.faultCode
              faultReasonReg := DADAODebugFaultReason.AccessFault.U
            }.otherwise {
              dataRequestBits :=
                0.U.asTypeOf(new DADAOMemReq(params.addrBits, params.dataBits))
              dataRequestBits.addr := loadExec.io.requestAddr
              dataRequestBits.write := false.B
              dataRequestBits.size := loadExec.io.requestSize
              dataRequestBits.wdata := 0.U
              dataRequestBits.wstrb := 0.U
              dataRequestBits.kind := DADAOMemKind.Data.U
              dataRequestAccepted := false.B
              memOwner := DADAOMemOwner.Data.U
            }
          }.elsewhen(storeExec.io.isStore) {
            decodedValidReg := true.B
            decodedIdReg := decoder.io.decoded.id
            decodedFormatReg := decoder.io.decoded.format
            decodedScopeReg := decoder.io.control.scope
            decodedNoopReg := false.B
            when(dataAccessCheck.io.fault) {
              halted := true.B
              faultReg := true.B
              faultCodeReg := dataAccessCheck.io.faultCode
              faultReasonReg := DADAODebugFaultReason.AccessFault.U
            }.otherwise {
              dataRequestBits :=
                0.U.asTypeOf(new DADAOMemReq(params.addrBits, params.dataBits))
              dataRequestBits.addr := storeExec.io.requestAddr
              dataRequestBits.write := true.B
              dataRequestBits.size := storeExec.io.requestSize
              dataRequestBits.wdata := storeExec.io.requestWdata
              dataRequestBits.wstrb := storeExec.io.requestWstrb
              dataRequestBits.kind := DADAOMemKind.Data.U
              dataRequestAccepted := false.B
              memOwner := DADAOMemOwner.Data.U
            }
          }.elsewhen(
            decoder.io.control.isNoop ||
              intExec.io.execValid
          ) {
            decodedValidReg := true.B
            decodedIdReg := decoder.io.decoded.id
            decodedFormatReg := decoder.io.decoded.format
            decodedScopeReg := decoder.io.control.scope
            decodedNoopReg := decoder.io.control.isNoop
            pcReg := nextRb0
          }.otherwise {
            halted := true.B
            faultReg := true.B
            faultCodeReg := DADAOFaultCode.Illi.U
            faultReasonReg := DADAODebugFaultReason.IlliOperand.U
            decodedIdReg := decoder.io.decoded.id
            decodedFormatReg := decoder.io.decoded.format
            decodedScopeReg := decoder.io.control.scope
          }
        }
      }.otherwise {
        // DATA ownership is reserved for RTL-010t load/store execution.
      }
    }
  }

  if (testMode) {
    when(io.pcInitValid.get && !halted) {
      resetCore(io.pcInit.get)
    }.elsewhen(reset.asBool) {
      resetCore(params.resetVector.U)
    }.otherwise {
      normalCycle()
    }
  } else {
    when(reset.asBool) {
      resetCore(params.resetVector.U)
    }.otherwise {
      normalCycle()
    }
  }

  if (testMode) {
    io.debugPc.get := pcReg
    io.debugDecodedValid.get := decodedValidReg
    io.debugWord.get := decodedWordReg
    io.debugId.get := decodedIdReg
    io.debugFormat.get := decodedFormatReg
    io.debugScope.get := decodedScopeReg
    io.debugNoop.get := decodedNoopReg
    io.debugFault.get := faultReg
    io.debugFaultCode.get := faultCodeReg
    io.debugFaultReason.get := faultReasonReg
    io.debugMemOwner.get := memOwner
    io.debugRasDone.get := regFile.rasControl.resp.done
    io.debugRasFault.get := regFile.rasControl.resp.fault
    io.debugRasMemReqValid.get :=
      regFile.rasControl.resp.memReqValid
    io.debugRasState.get := regFile.rasControl.resp.state
    io.debugCfxReadData.get := cfx.io.testReadData
    io.debugCfxReadValid.get := cfx.io.testReadValid
    io.debugCfxStatus.get := cfx.io.status
    intExec.io.testRegWrite.get := io.testRegWrite.get
    intExec.io.debugReadBank.get := io.debugRegBank.get
    intExec.io.debugReadAddr.get := io.debugRegAddr.get
    io.debugRegData.get := intExec.io.debugReadData.get
    io.debugDataRequestAddr.get := dataRequestBits.addr
    io.debugDataRequestWrite.get := dataRequestBits.write
    io.debugDataRequestWdata.get := dataRequestBits.wdata
    io.debugDataRequestWstrb.get := dataRequestBits.wstrb
    io.debugDataResponseData.get := io.mem.resp.bits.rdata
    io.debugLoadWrite.get := loadExec.io.write.valid
    io.debugLoadWriteData.get := loadExec.io.write.data
  }
}
