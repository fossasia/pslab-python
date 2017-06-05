# This library allows P2P connections for LoRa modules that are built with the SX1276 chip from Semtech
# It does not implement the LoRaWAN stack, and is only meant for standalone long range communications
# Register definitions adapted from sample code for SEMTECH SX1276
import time

def connect(SPI):
	return SX1276(SPI)


class SX1276():
	name = 'SX1276'
	#********************LoRA mode***************************/
	LR_RegFifo                                     = 0x00
	#Common settings
	LR_RegOpMode                                   = 0x01
	LR_RegFrMsb                                    = 0x06
	LR_RegFrMid                                    = 0x07
	LR_RegFrLsb                                    = 0x08
	#Tx settings
	LR_RegPaConfig                                 = 0x09
	LR_RegPaRamp                                   = 0x0A
	LR_RegOcp                                      = 0x0B
	#Rx settings
	LR_RegLna                                      = 0x0C
	#LoRa registers
	LR_RegFifoAddrPtr                              = 0x0D
	LR_RegFifoTxBaseAddr                           = 0x0E
	LR_RegFifoRxBaseAddr                           = 0x0F
	LR_RegFifoRxCurrentaddr                        = 0x10
	LR_RegIrqFlagsMask                             = 0x11
	LR_RegIrqFlags                                 = 0x12
	LR_RegRxNbBytes                                = 0x13
	LR_RegRxHeaderCntValueMsb                      = 0x14
	LR_RegRxHeaderCntValueLsb                      = 0x15
	LR_RegRxPacketCntValueMsb                      = 0x16
	LR_RegRxPacketCntValueLsb                      = 0x17
	LR_RegModemStat                                = 0x18
	LR_RegPktSnrValue                              = 0x19
	LR_RegPktRssiValue                             = 0x1A
	LR_RegRssiValue                                = 0x1B
	LR_RegHopChannel                               = 0x1C
	LR_RegModemConfig1                             = 0x1D
	LR_RegModemConfig2                             = 0x1E
	LR_RegSymbTimeoutLsb                           = 0x1F
	LR_RegPreambleMsb                              = 0x20
	LR_RegPreambleLsb                              = 0x21
	LR_RegPayloadLength                            = 0x22
	LR_RegMaxPayloadLength                         = 0x23
	LR_RegHopPeriod                                = 0x24
	LR_RegFifoRxByteAddr                           = 0x25

	#I/O settings
	REG_LR_DIOMAPPING1                             = 0x40
	REG_LR_DIOMAPPING2                             = 0x41
	#Version
	REG_LR_VERSION                                 = 0x42
	#Additional settings
	REG_LR_PLLHOP                                  = 0x44
	REG_LR_TCXO                                    = 0x4B
	REG_LR_PADAC                                   = 0x4D
	REG_LR_FORMERTEMP                              = 0x5B

	REG_LR_AGCREF                                  = 0x61
	REG_LR_AGCTHRESH1                              = 0x62
	REG_LR_AGCTHRESH2                              = 0x63
	REG_LR_AGCTHRESH3                              = 0x64

	#/********************FSK/ook mode***************************/
	RegFIFO  	 			   = 0x00				#FIFO
	RegOpMode 	 			   = 0x01			#Operation mode
	RegBitRateMsb 		   = 0x02				#BR MSB
	RegBitRateLsb 		   = 0x03				#BR LSB
	RegFdevMsb	 			   = 0x04			#FD MSB
	RegFdevLsb	 			   = 0x05 			#FD LSB
	RegFreqMsb	 			   = 0x06			#Freq MSB
	RegFreqMid	 			   = 0x07 			#Freq Middle byte
	RegFreqLsb   		   = 0x08				#Freq LSB
	RegPaConfig			   = 0x09
	RegPaRamp				   = 0x0a
	RegOcp						   = 0x0b
	RegLna						   = 0x0c
	RegRxConfig			   = 0x0d
	RegRssiConfig		   = 0x0e
	RegRssiCollision    = 0x0f
	RegRssiThresh		   = 0x10
	RegRssiValue			   = 0x11
	RegRxBw					   = 0x12
	RegAfcBw					   = 0x13
	RegOokPeak				   = 0x14
	RegOokFix				   = 0x15
	RegOokAvg				   = 0x16

	RegAfcFei				   = 0x1a	
	RegAfcMsb				   = 0x1b
	RegAfcLsb				   = 0x1c
	RegFeiMsb				   = 0x1d
	RegFeiLsb				   = 0x1e
	RegPreambleDetect	   = 0x1f
	RegRxTimeout1		   = 0x20
	RegRxTimeout2		   = 0x21
	RegRxTimeout3		   = 0x22
	RegRxDelay				   = 0x23
	RegOsc  	 				   = 0x24			#Set OSC 
	RegPreambleMsb		   = 0x25
	RegPreambleLsb		   = 0x26
	RegSyncConfig		   = 0x27
	RegSyncValue1		   = 0x28
	RegSyncValue2		   = 0x29
	RegSyncValue3		   = 0x2a
	RegSyncValue4		   = 0x2b
	RegSyncValue5		   = 0x2c
	RegSyncValue6		   = 0x2d
	RegSyncValue7		   = 0x2e
	RegSyncValue8		   = 0x2f
	RegPacketConfig1		   = 0x30
	RegPacketConfig2		   = 0x31
	RegPayloadLength		   = 0x32
	RegNodeAdrs			   = 0x33
	RegBroadcastAdrs		   = 0x34
	RegFifoThresh		   = 0x35
	RegSeqConfig1		   = 0x36
	RegSeqConfig2		   = 0x37
	RegTimerResol		   = 0x38
	RegTimer1Coef		   = 0x39
	RegTimer2Coef		   = 0x3a
	RegImageCal			   = 0x3b
	RegTemp					   = 0x3c
	RegLowBat				   = 0x3d
	RegIrqFlags1			   = 0x3e
	RegIrqFlags2			   = 0x3f
	RegDioMapping1		   = 0x40
	RegDioMapping2		   = 0x41
	RegVersion				   = 0x42

	RegPllHop				   = 0x44
	RegPaDac					   = 0x4d
	RegBitRateFrac		   = 0x5d

	CR_SETTINGS = {'4_5': 0x01,'4_6': 0x02,'4_7': 0x03,'4_8': 0x04}
	sx1276_7_8FreqTbl = [[0x6C,0x80,0x00]] 		#434MHz
	sx1276_7_8PowerTbl = [0xFF,0xFC,0xF9,0xF6]  #20dbm,17dbm,14dbm,11dbm
	sx1276_7_8SpreadFactorTbl = [6,7,8,9,10,11,12]
	
	#7.8KHz,10.4KHz,15.6KHz,20.8KHz,31.2KHz,41.7KHz,62.5KHz,125KHz,250KHz,500KHz
	sx1276_7_8LoRaBwTbl = [0,1,2,3,4,5,6,7,8,9]
	sampleData = [ord(a) for a in "Mark1 Lora sx1276_7_8"]
	
	mode = 0x01          #lora mode
	Freq_Sel = 0x00      #433M
	Power_Sel = 0x00
	Lora_Rate_Sel = 0x06
	BandWide_Sel = 0x07
	Fsk_Rate_Sel = 0x00

	def __init__(self,SPI,**args):
		self.SPI = SPI
		self.SPI.set_parameters(2,6,1,0)
		self.CR = self.CR_SETTINGS['4_5']
		self.CRC = 1
		self.name = 'SX1276'

		self.config()
		self.LoRaEntryRX();


	def standby(self):
		self.SPIWrite(self.LR_RegOpMode,[0x09]) #Low freq mode
		#self.SPIWrite(self.LR_RegOpMode,[0x01]) #High freq mode

	def sleep(self):
		self.SPIWrite(self.LR_RegOpMode,[0x08])

	def EntryLoRa(self):
		self.SPIWrite(self.LR_RegOpMode,[0x88]) #Low freq mode
		#self.SPIWrite(self.LR_RegOpMode,[0x80]) #High freq mode

	def LoRaClearIRQ(self):
		self.SPIWrite(self.LR_RegIrqFlags,[0xFF])

	def LoRaEntryRX(self):
		self.config()										#setting base parameter
		self.SPIWrite(self.REG_LR_PADAC,[0x84])				#Normal and Rx
		self.SPIWrite(self.LR_RegHopPeriod,[0xFF])			#RegHopPeriod NO FHSS
		self.SPIWrite(self.REG_LR_DIOMAPPING1,[0x01])		#DIO0=00, DIO1=00, DIO2=00, DIO3=01
		
		self.SPIWrite(self.LR_RegIrqFlagsMask,[0x3F])		#Open RxDone interrupt & Timeout
		self.LoRaClearIRQ()
		
		self.SPIWrite(self.RegPayloadLength,[21])           #RegPayloadLength  21byte(this register must difine when the data long of one byte in SF is 6)

		addr = self.SPIRead(self.LR_RegFifoRxBaseAddr,1)[0]  #Read RxBaseAddr
		print ('rx address',addr, self.SPIRead(self.LR_RegFifoRxCurrentaddr,1)[0])
		self.SPIWrite(self.LR_RegFifoAddrPtr,[addr])		#RxBaseAddr -> FiFoAddrPtr
		self.SPIWrite(self.LR_RegOpMode,[0x8D])				#Continuous Rx Mode//Low Frequency Mode
		#self.SPIWrite(self.LR_RegOpMode,[0x05])  			#High freq mode

		while 1:
			if self.SPIRead(self.LR_RegModemStat,1)[0]&0x04 == 0x04:  #Rx-on going RegModemStat
				print ('done')
				break
			print ('waiting :',time.ctime(),self.SPIRead(self.LR_RegModemStat,1))
		
	def LoRaReadRSSI(self):
		tmp = self.SPIRead(self.LR_RegRssiValue,1)[0]
		tmp = tmp+127-137			#127:Max RSSI, 137:RSSI offset
		return tmp

	def LoRaRxPacket(self):
		#if get_state('ID1'):   #IRQ is high
		time.sleep(0.01)
		addr = self.SPIRead(self.LR_RegFifoRxCurrentaddr,1)[0]   #last packet addr
		self.SPIWrite(self.LR_RegFifoAddrPtr,[addr])
		if self.sx1276_7_8SpreadFactorTbl[self.Lora_Rate_Sel] == 6: #Spread Factor = 6
			packet_size = 21
		else:
			packet_size = self.SPIRead(self.LR_RegRxNbBytes,1)[0]
		RxData = self.SPIRead(0x00,packet_size)
		self.LoRaClearIRQ()
		return RxData

	def LoRaEntryTX(self):
		length = 21
		self.config()										#setting base parameter
		self.SPIWrite(self.REG_LR_PADAC,[0x87])				#Tx at 20dbm
		self.SPIWrite(self.LR_RegHopPeriod,[0x00])			#RegHopPeriod NO FHSS
		self.SPIWrite(self.REG_LR_DIOMAPPING1,[0x41])		#DIO0=01, DIO1=00, DIO2=00, DIO3=01
		
		self.LoRaClearIRQ()
		self.SPIWrite(self.LR_RegIrqFlagsMask,[0xF7])		#Open TxDone interrupt
		self.SPIWrite(self.RegPayloadLength,[length])           #RegPayloadLength  21byte

		addr = self.SPIRead(self.LR_RegFifoTxBaseAddr,1)[0]  #Read TxBaseAddr
		print ('tx address',addr)
		self.SPIWrite(self.LR_RegFifoAddrPtr,[addr])		#TxBaseAddr -> FiFoAddrPtr

		while 1:
			if self.SPIRead(self.LR_RegPayloadLength,1)[0] == length:  #Rx-on going RegModemStat
				print ('done')
				break
			print ('waiting :',time.ctime(),self.SPIRead(self.LR_RegPayloadLength,1))
			time.sleep(0.1)

	def LoRaTxPacket(self,dataArray):
		self.SPIWrite(0x00,dataArray)
		self.SPIWrite(self.LR_RegOpMode,[0x8B]) #TX Mode
		#while not self.get_state('ID1'): 
		time.sleep(0.1)
		self.SPIRead(self.LR_RegIrqFlags,1)
		self.LoRaClearIRQ()
		self.standby()
		print (len(lora.sampleData),lora.sampleData)
			
	def ReadRSSI(self):
		tmp = self.SPIRead(self.LR_RegIrqFlagsMask,1)[0]
		tmp >>=1	
		return 127-tmp

	def config(self):
		self.sleep()
		time.sleep(0.015)
		self.EntryLoRa()
		self.SPIWrite(self.LR_RegFrMsb,self.sx1276_7_8FreqTbl[self.Freq_Sel])
		self.SPIWrite(self.LR_RegPaConfig,[self.sx1276_7_8PowerTbl[self.Power_Sel]])
				
		self.SPIWrite(self.LR_RegOcp,[0x0B]) #Close ocp
		self.SPIWrite(self.LR_RegLna,[0x23]) #RegLNA , HIGH, LNA enable
		
		if self.sx1276_7_8SpreadFactorTbl[self.Lora_Rate_Sel]==6:
			self.SPIWrite(self.LR_RegModemConfig1,[(self.sx1276_7_8LoRaBwTbl[self.BandWide_Sel]<<4)+(self.CR<<1)+0x01]) 			# Enable CRC Enable(0x02) & Error Coding rate 4/5(0x01), 4/6(0x02), 4/7
			self.SPIWrite(self.LR_RegModemConfig2,[(self.sx1276_7_8SpreadFactorTbl[self.Lora_Rate_Sel]<<4)+(self.CRC<<2)+0x03]) 			# SFactor &  LNA gain set by the internal AGC loop 
			tmp = self.SPIRead(0x31)[0]
			tmp&=0xF8;tmp|=0x05
			self.SPIWrite(0x31,[tmp])
			self.SPIWrite(0x37,[0x0C])
		else:
			self.SPIWrite(self.LR_RegModemConfig1,[(self.sx1276_7_8LoRaBwTbl[self.BandWide_Sel]<<4)+(self.CR<<1)+0x00])
			self.SPIWrite(self.LR_RegModemConfig2,[(self.sx1276_7_8SpreadFactorTbl[self.Lora_Rate_Sel]<<4)+(self.CRC<<2)+0x03])
				
		self.SPIWrite(self.LR_RegSymbTimeoutLsb,[0xFF])  #Max timeout
		self.SPIWrite(self.LR_RegPreambleMsb,[0x00])
		self.SPIWrite(self.LR_RegPreambleLsb,[12])     #RegPreambleLsb 8+4=12byte Preamble
		
		self.SPIWrite(self.REG_LR_DIOMAPPING2,[0x01])  #RegDioMapping2 DIO5=00, DIO4=01
		self.standby()

	def SPIWrite(self,adr,byteArray):
		return self.SPI.xfer('CS1',[0x80|adr]+byteArray)[1:]

	def SPIRead(self,adr,total_bytes):
		return self.SPI.xfer('CS1',[adr]+[0]*total_bytes)[1:]

	def getRaw(self):
		val = self.SPIRead(0x02,1)
		return val



if __name__ == "__main__":
	'''
	Example code to test LoRa modules.
	Set mode = 0 to enable receiver , or mode = 1 to enable a periodic transmitter
	
	Frequency = 434MHz #Use the frequency specified by the module being used
	transmission is at 17db
	BW = 125KHz
	Spreading Factor (SF) = 12
	Coding rate(CR) = 4/5   #The numerator is always 4, and the argument passed to the init function is the denominator
	'''
	RX = 0;	TX=1
	mode = RX
	from PSL import sciencelab
	I= sciencelab.connect()
	lora = SX1276(I.SPI,434e6,boost=True,power=17,BW=125e3,SF=12,CR=5)
	lora.crc()  #Enable CRC
	cntr=0      #Incrementing counter for TX mode
	while 1:
		time.sleep(0.01)
		if mode==TX:
			lora.beginPacket()   #Enable writing mode
			lora.write([ord(a) for a in ":"]+[cntr])  #write some bytes
			print (time.ctime(),cntr, hex(lora.SPIRead(lora.REG_OP_MODE)[0]))
			lora.endPacket()    #Switch to transmit mode, and send the data
			cntr+=1
			if cntr==255:cntr=0
		else:
			packet_size = lora.parsePacket()
			if packet_size:  #If some data was received
				print ('got packet')
				print 'data',lora.readAll()  #Print the data
				print ('Rssi',lora.packetRssi(),lora.packetSnr())  #Print signal strength and signal to noise ratio


