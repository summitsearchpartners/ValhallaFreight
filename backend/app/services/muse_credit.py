"""Original Muse PDF with applicant values over the existing blanks."""
from io import BytesIO
from pathlib import Path
from hashlib import sha256

TEMPLATE = Path(__file__).resolve().parent.parent / "muse-credit-application.pdf"
TEMPLATE_SHA256 = sha256(TEMPLATE.read_bytes()).hexdigest()
# x, top, width, height in PDF points, on the original 612 x 792 page.
FIELDS = [
    ("company_name","Full name of your company",145,100,392,11,True),
    ("billing_street","Billing street address",144,132,142,11,True),
    ("physical_street","Physical street address",393,132,144,11,True),
    ("billing_city","Billing city",73,164,135,11,True),
    ("billing_state","Billing state",211,164,34,11,True),
    ("billing_zip","Billing ZIP",247,164,39,11,True),
    ("physical_city","Physical city",320,164,120,11,True),
    ("physical_state","Physical state",442,164,36,11,True),
    ("physical_zip","Physical ZIP",480,164,57,11,True),
    ("telephone","Telephone number",157,196,129,11,True),
    ("fax","Fax number",373,196,164,11,False),
    ("president","President",115,218,171,11,True),
    ("controller","Controller",366,218,171,11,True),
    ("ap_contact","Accounts payable contact",184,240,102,11,True),
    ("ap_email","Accounts payable email",398,240,139,11,True),
    ("other_business","Other business type",475,273,62,10,False),
    ("federal_id","Federal ID number",113,284,65,11,True),
    ("incorporation","State and date of incorporation / formation",453,284,84,11,True),
    ("parent_company","Parent company",145,306,141,11,False),
    ("branches","Branches",363,306,174,11,False),
    ("bank_name","Bank name",126,375,160,11,True),
    ("bank_phone","Bank phone",356,375,181,11,True),
    ("bank_contact","Bank contact",135,397,151,11,True),
    ("bank_fax","Bank fax",347,397,190,11,False),
    ("checking_account","Checking account number",143,419,143,11,True),
    ("credit_account","Line of credit account number",408,419,129,11,False),
    ("signature","Authorized signature (type your full name)",73,514,244,10,True),
    ("title","Signer title",321,514,216,10,True),
    ("print_name","Print name",73,544,244,12,True),
    ("date","Date",321,544,216,12,True),
]
BUSINESS = {"corporation": (169,255), "partnership":(257,255), "sole_proprietor":(347,255), "other":(435,255)}


def filled_pdf(data: dict) -> bytes:
    from reportlab.pdfgen import canvas
    from reportlab.pdfbase.pdfmetrics import stringWidth
    from pypdf import PdfReader, PdfWriter
    layer=BytesIO()
    pen=canvas.Canvas(layer,pagesize=(612,792))
    pen._code.append("BT 0 Tc 0 Tw 100 Tz ET")
    for key,_,x,top,width,height,_ in FIELDS:
        text=str(data.get(key,""))
        size=9
        while size>4 and stringWidth(text,"Helvetica",size)>width:
            size-=0.25
        pen.setFont("Helvetica",size)
        pen.drawString(x,792-top-height+2,text)
    x,y=BUSINESS[data["business_type"]]
    pen.setFont("Helvetica-Bold",10);pen.drawString(x,792-y-10,"X")
    pen.save();layer.seek(0)
    source=PdfReader(TEMPLATE)
    source.pages[0].merge_page(PdfReader(layer).pages[0])
    writer=PdfWriter();writer.add_page(source.pages[0])
    output=BytesIO();writer.write(output)
    return output.getvalue()
