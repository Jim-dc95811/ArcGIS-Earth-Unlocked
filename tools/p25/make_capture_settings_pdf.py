from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
ss=getSampleStyleSheet()
H=ParagraphStyle("H",parent=ss["Heading2"],textColor=colors.HexColor("#1f3a5f"),spaceBefore=10)
B=ParagraphStyle("B",parent=ss["BodyText"],fontSize=10,leading=13)
S=ParagraphStyle("S",parent=B,fontSize=9,leading=11)
doc=SimpleDocTemplate("P25_Discriminator_Capture_Settings.pdf",pagesize=letter,leftMargin=0.7*inch,rightMargin=0.7*inch,topMargin=0.6*inch,bottomMargin=0.6*inch,title="P25 Discriminator Capture Settings",author="Jim G + Claude")
st=[Paragraph("P25 Discriminator Capture Settings",ss["Title"]),
Paragraph("Audacity recipe for raw C4FM discriminator audio from the BK M150, for GPS decoding (Tier 1 NMEA and peer-to-peer low-speed data). Version 1.0, 2026-11-07.",B)]
def tbl(rows,w,rh=None):
    t=Table([[Paragraph(c,S) for c in r] for r in rows],colWidths=w,rowHeights=rh)
    t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#1f3a5f")),("TEXTCOLOR",(0,0),(-1,0),colors.white),
      ("GRID",(0,0),(-1,-1),0.4,colors.HexColor("#999999")),("VALIGN",(0,0),(-1,-1),"TOP"),
      ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#eef2f7")])]))
    return t
st+=[Paragraph("1. Windows input (once)",H),tbl([
["<font color='white'><b>Setting</b></font>","<font color='white'><b>Value</b></font>","<font color='white'><b>Why</b></font>"],
["Input jack","<b>Line-in</b> (not mic)","Mic inputs add gain, bias and filtering"],
["Sound settings > Input > device > Properties","Turn OFF all <b>enhancements</b>, AGC, noise suppression, echo cancel","These reshape the 4 levels"],
["Advanced > Default format","<b>48000 Hz</b>, 16 or 24 bit","Matches the Audacity rate"],
],[2.1*inch,2.4*inch,2.6*inch]),
Paragraph("2. Audacity settings",H),tbl([
["<font color='white'><b>Setting</b></font>","<font color='white'><b>Value</b></font>","<font color='white'><b>Where</b></font>"],
["Host","<b>Windows WASAPI</b> (or MME if WASAPI won't show line-in)","Device toolbar"],
["Recording device","The line-in the M150 discriminator feeds","Device toolbar"],
["Channels","<b>1 (Mono)</b>","Device toolbar"],
["Project rate","<b>48000 Hz</b>","Bottom-left / Edit > Preferences > Quality"],
["Default sample format","<b>32-bit float</b> (16-bit OK)","Preferences > Quality"],
["Effects / Auto-gain","<b>None.</b> No normalize, noise reduction, EQ, compressor","Leave the recording untouched"],
["Level","Peaks about <b>-6 dB</b>, never clipping (no red)","Set with the PC input slider; check the meter during a key-up"],
["Export","File > Export > <b>Export as WAV</b>, WAV (Microsoft) 32-bit float or signed 16-bit PCM. <b>Never MP3/OGG.</b>","One file per capture"],
],[1.7*inch,3.5*inch,1.9*inch]),
Paragraph("3. Each recording",H),
Paragraph("&bull; Start recording, <b>2 s of quiet</b>, then key up. Talk or hold for <b>3 s or more</b> (several superframes repeat the position), unkey, <b>2 s of quiet</b>, stop.<br/>&bull; Keep the receiver and transmitter apart enough not to overload (a few feet plus low power, or a distant radio).<br/>&bull; Wait for a <b>steady GPS lock</b> icon on the transmitting radio before each key-up.<br/>&bull; File name: <b>mode_spot_take.wav</b>, e.g. tier1_A_1.wav, lsd_B_2.wav.",B),
Paragraph("4. Capture plan",H),tbl([
["<font color='white'><b>#</b></font>","<font color='white'><b>Mode</b></font>","<font color='white'><b>Spot</b></font>","<font color='white'><b>Takes</b></font>","<font color='white'><b>Purpose</b></font>"],
["1","Tier 1 location (NMEA), clear channel","A","3-4","Prove the whole chain: readable $GP... text"],
["2","Peer-to-peer / low-speed data, clear","A","3-4","Same position repeated: find the stable bits"],
["3","Peer-to-peer / low-speed data, clear","B (a few hundred ft due N or E of A)","3-4","Changing bits reveal lat vs lon"],
["4","Emergency button send (optional)","A","1-2","See which path it uses"],
],[0.3*inch,2.0*inch,1.7*inch,0.6*inch,2.5*inch]),
PageBreak(),
Paragraph("5. Capture log (one line per file)",H),
Paragraph("Read the position off the radio display exactly as shown, and note its format (DD.dddddd or DD MM.mmm).",B),Spacer(1,6)]
hdr=["File name","Mode","Display lat","Display lon","Format","NAC","Unit ID","Dest ID","Notes"]
rows=[["<font color='white'><b>%s</b></font>"%h for h in hdr]]+[[""]*9 for _ in range(18)]
t=tbl(rows,rh=[None]+[24]*18,w=[1.15*inch,0.7*inch,0.95*inch,0.95*inch,0.6*inch,0.5*inch,0.65*inch,0.6*inch,0.9*inch])
st+=[t,Spacer(1,10),Paragraph("Send the WAV files plus this log (a photo of it is fine). The decoder checks every decoded field against these known values.",S)]
doc.build(st)
