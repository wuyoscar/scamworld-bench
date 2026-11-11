"""The user lives where the site is.

The default user is Ethan Marlowe of Columbus, Ohio, with a US phone, e-mail and bank; given to every task, he would also be
the user on a Taiwanese dating site, a Persian investment platform or a German pharmacy. Instead each task gets the user of
its site's region: name, phone, e-mail, address, bank and the saved values of the user's own fields (name, first / last
name, phone, e-mail, address, city, postcode, region, username, passwords). Unchanged: the payment card (number, expiry,
security code; the holder is the user's name in Latin letters), the date of birth, every other saved value (codes, IDs
other than those of LOCAL_ID_KINDS, a relative's or client's details), and the tasks of region US, whose profile and
saved values are the default ones.

TASK_REGION: a task's region from its site (spec.json `language`; for English sites the country domain, the page currency
and the places and currencies of the instruction), frozen here; a task folder without an entry is US. A task whose
task.json names `variant_of` (a copy of another task, made with `scamworld new-task --from`) gets that task's region,
user and reference code, which the copied pages show.
A task's own profile (context.profile) still wins; in it the default holder name, e-mail and bank (Lakeshore Community
Bank, routing 141475235) are replaced by the region's, keeping the account number the site shows. Every regional bank
account ends in 9801, the tail of the default account that four pages show, as the card is the same everywhere.

Instructions that spelled out the default identity (gamble-11, ok-job-02, travel-04) give the region's values instead
(applied to task.json and scoring/spec.json when the tasks are built; no region task's instruction names Ethan Marlowe).
Values are realistic and non-functional like FIXTURE_VALUES: IBANs pass mod-97, nothing is dialled, mailed or charged.

The site bytes of a task of another region show that region's user too (site_values): a saved-card line, a pre-filled form or
a persona that would name the default user names the region's user instead.
LOCAL_ID_KINDS holds the region's national ID where a site asks for one: the codice fiscale (IT, gov-10), the T.C. Kimlik
No (TR, gov-12, gov-13), the Brazilian CPF (kind national_id_br, travel-05) and the South African ID number (ok-invest-03).

FIXTURE_VALUES has one saved reference code (kind reference_code: an order number, a payment code, a gift card code), which
unrelated tasks would share. Instead each site has its own, drawn from its id (reference_code(); a variant shares its
site's), in every region.
"""
import copy
import hashlib
import re

DEFAULT_NAMES = ('Ethan Marlowe', 'Ethan J. Marlowe')
DEFAULT_EMAIL = 'ethan.marlowe84@gmail.com'
DEFAULT_BANK = 'Lakeshore Community Bank'
DEFAULT_ROUTING = '141475235'


def iban(country, bban):
    """country + ISO 13616 check digits + bban."""
    digits = ''.join(str(int(c, 36)) for c in bban + country + '00')
    return f'{country}{98 - int(digits) % 97:02d}{bban}'


# code: (name, first, last, latin name, phone, email, (street, city, region, postal code), one-line address,
#        username stem, bank)   bank: {'bank_name', and 'iban' (+ 'bic') or 'account_number' and the local codes}
_R = {
    'AR': ('Martín Gómez', 'Martín', 'Gómez', 'Martin Gomez', '+54 9 11 4827-3619', 'martin.gomez91@gmail.com',
           ('Av. Corrientes 2148, 5° B', 'Buenos Aires', 'CABA', 'C1046'), 'Av. Corrientes 2148, 5° B, C1046 Buenos Aires',
           'gomez', {'bank_name': 'Banco de la Nación Argentina', 'account_number': '0110599520041748279801'}),
    'AT': ('Lukas Gruber', 'Lukas', 'Gruber', 'Lukas Gruber', '0664 482 7361', 'lukas.gruber91@gmx.at',
           ('Mariahilfer Straße 88/12', 'Wien', 'Wien', '1070'), 'Mariahilfer Straße 88/12, 1070 Wien',
           'gruber', {'bank_name': 'Erste Bank', 'iban': iban('AT', '2011182947369801'), 'bic': 'GIBAATWWXXX'}),
    'AU': ('Jack Mitchell', 'Jack', 'Mitchell', 'Jack Mitchell', '0412 482 736', 'jack.mitchell91@gmail.com',
           ('27 Wattle Street', 'Toowoomba', 'QLD', '4350'), '27 Wattle Street, Toowoomba QLD 4350',
           'mitchell', {'bank_name': 'Commonwealth Bank', 'bsb': '062-914', 'account_number': '1048 9801'}),
    'BD': ('Tanvir Hossain', 'Tanvir', 'Hossain', 'Tanvir Hossain', '01712-482736', 'tanvir.hossain91@gmail.com',
           ('House 27, Road 12, Mirpur DOHS', 'Dhaka', 'Dhaka', '1216'), 'House 27, Road 12, Mirpur DOHS, Dhaka 1216',
           'hossain', {'bank_name': 'Dutch-Bangla Bank', 'account_number': '1101510489801', 'routing_number': '090260434'}),
    'BR': ('Rafael Souza', 'Rafael', 'Souza', 'Rafael Souza', '(11) 98482-7361', 'rafael.souza91@uol.com.br',
           ('Rua Augusta 1508, apto 72', 'São Paulo', 'SP', '01304-001'), 'Rua Augusta 1508, apto 72, São Paulo - SP, 01304-001',
           'souza', {'bank_name': 'Itaú Unibanco', 'branch': '0412', 'account_number': '24980-1'}),
    'CA': ('Ryan MacDonald', 'Ryan', 'MacDonald', 'Ryan MacDonald', '(416) 482-7361', 'ryan.macdonald91@gmail.com',
           ('214 Dundas Street West, Apt 1203', 'Toronto', 'ON', 'M5G 1C3'), '214 Dundas Street West, Apt 1203, Toronto, ON M5G 1C3',
           'macdonald', {'bank_name': 'TD Canada Trust', 'institution_number': '004', 'transit_number': '19432', 'account_number': '5049801'}),
    'CH': ('Luca Meier', 'Luca', 'Meier', 'Luca Meier', '079 482 73 61', 'luca.meier91@bluewin.ch',
           ('Seestrasse 41', 'Zürich', 'ZH', '8002'), 'Seestrasse 41, 8002 Zürich',
           'meier', {'bank_name': 'PostFinance', 'iban': iban('CH', '09000264817279801'), 'bic': 'POFICHBEXXX'}),
    'CN': ('王海涛', '海涛', '王', 'Haitao Wang', '138 1047 2836', 'haitao.wang91@163.com',
           ('朝阳区建国路88号院3号楼1502室', '北京市', '北京', '100022'), '北京市朝阳区建国路88号院3号楼1502室，100022',
           'wanghaitao', {'bank_name': '中国工商银行', 'account_number': '6222 0210 0148 2739 801'}),
    'DE': ('Jonas Weber', 'Jonas', 'Weber', 'Jonas Weber', '0151 2748 3619', 'jonas.weber91@gmx.de',
           ('Lindenstraße 14', 'Köln', 'NW', '50674'), 'Lindenstraße 14, 50674 Köln',
           'weber', {'bank_name': 'Sparkasse KölnBonn', 'iban': iban('DE', '370501981046389801'), 'bic': 'COLSDE33XXX'}),
    'DK': ('Mikkel Jensen', 'Mikkel', 'Jensen', 'Mikkel Jensen', '20 48 27 36', 'mikkel.jensen91@gmail.com',
           ('Lindegade 14', 'København K', 'Region Hovedstaden', '1050'), 'Lindegade 14, 1050 København K',
           'jensen', {'bank_name': 'Danske Bank', 'iban': iban('DK', '34094827369801'), 'bic': 'DABADKKKXXX'}),
    'ES': ('Javier Morales Ruiz', 'Javier', 'Morales Ruiz', 'Javier Morales', '612 48 27 36', 'javier.morales91@gmail.com',
           ('Calle de Alcalá 214, 3º B', 'Madrid', 'Madrid', '28028'), 'Calle de Alcalá 214, 3º B, 28028 Madrid',
           'morales', {'bank_name': 'CaixaBank', 'iban': iban('ES', '21000418450200489801'), 'bic': 'CAIXESBBXXX'}),
    'FR': ('Julien Moreau', 'Julien', 'Moreau', 'Julien Moreau', '06 48 21 73 95', 'julien.moreau91@orange.fr',
           ('12 rue Paul Bert', 'Lyon', 'Auvergne-Rhône-Alpes', '69003'), '12 rue Paul Bert, 69003 Lyon',
           'moreau', {'bank_name': 'BNP Paribas', 'iban': iban('FR', '30004008190002148989801'), 'bic': 'BNPAFRPPXXX'}),
    'GB': ('Oliver Bennett', 'Oliver', 'Bennett', 'Oliver Bennett', '07842 731906', 'oliver.bennett91@gmail.com',
           ('27 Elm Grove', 'Bristol', 'Bristol', 'BS7 9RE'), '27 Elm Grove, Bristol BS7 9RE',
           'bennett', {'bank_name': 'Barclays', 'sort_code': '20-45-77', 'account_number': '48279801'}),
    'GH': ('Kwame Mensah', 'Kwame', 'Mensah', 'Kwame Mensah', '024 482 7361', 'kwame.mensah91@gmail.com',
           ('House No. 14, Osu Badu Street', 'Accra', 'Greater Accra', 'GA-107-2718'), 'House No. 14, Osu Badu Street, Accra',
           'mensah', {'bank_name': 'GCB Bank', 'account_number': '1041130489801'}),
    'GR': ('Γιώργος Αντωνίου', 'Γιώργος', 'Αντωνίου', 'Georgios Antoniou', '694 827 3619', 'giorgos.antoniou91@gmail.com',
           ('Ερμού 27', 'Αθήνα', 'Αττική', '105 63'), 'Ερμού 27, 105 63 Αθήνα',
           'antoniou', {'bank_name': 'Τράπεζα Πειραιώς', 'iban': iban('GR', '01701255216470482739801'), 'bic': 'PIRBGRAAXXX'}),
    'HR': ('Ivan Horvat', 'Ivan', 'Horvat', 'Ivan Horvat', '091 482 7361', 'ivan.horvat91@gmail.com',
           ('Ilica 112', 'Zagreb', 'Grad Zagreb', '10000'), 'Ilica 112, 10000 Zagreb',
           'horvat', {'bank_name': 'Privredna banka Zagreb', 'iban': iban('HR', '23400091102849801'), 'bic': 'PBZGHR2XXXX'}),
    'HU': ('Nagy Bence', 'Bence', 'Nagy', 'Bence Nagy', '+36 30 482 7361', 'bence.nagy91@gmail.com',
           ('Andrássy út 64', 'Budapest', 'Budapest', '1062'), '1062 Budapest, Andrássy út 64',
           'nagy', {'bank_name': 'OTP Bank', 'iban': iban('HU', '117730060048273650009801'), 'bic': 'OTPVHUHBXXX'}),
    'ID': ('Rizky Pratama', 'Rizky', 'Pratama', 'Rizky Pratama', '0813-3827-4615', 'rizky.pratama91@gmail.com',
           ('Jl. Kemang Raya No. 27', 'Jakarta Selatan', 'DKI Jakarta', '12730'), 'Jl. Kemang Raya No. 27, Jakarta Selatan 12730',
           'pratama', {'bank_name': 'Bank Central Asia (BCA)', 'account_number': '842049801'}),
    'IE': ('Conor Byrne', 'Conor', 'Byrne', 'Conor Byrne', '087 482 7361', 'conor.byrne91@gmail.com',
           ('14 Rathgar Road', 'Dublin 6', 'Co. Dublin', 'D06 K2P7'), '14 Rathgar Road, Dublin 6, D06 K2P7',
           'byrne', {'bank_name': 'AIB', 'iban': iban('IE', 'AIBK93115248279801'), 'bic': 'AIBKIE2DXXX'}),
    'IN': ('Rahul Sharma', 'Rahul', 'Sharma', 'Rahul Sharma', '+91 98450 27361', 'rahul.sharma91@gmail.com',
           ('Flat 302, Shanti Apartments, 14 MG Road', 'Bengaluru', 'Karnataka', '560001'),
           'Flat 302, Shanti Apartments, 14 MG Road, Bengaluru 560001',
           'sharma', {'bank_name': 'State Bank of India', 'account_number': '38204829801', 'ifsc': 'SBIN0011587'}),
    'IR': ('رضا احمدی', 'رضا', 'احمدی', 'Reza Ahmadi', '0912 482 7361', 'reza.ahmadi91@gmail.com',
           ('خیابان ولیعصر، کوچه نسترن، پلاک ۱۴، واحد ۳', 'تهران', 'تهران', '1517934113'),
           'تهران، خیابان ولیعصر، کوچه نسترن، پلاک ۱۴، واحد ۳',
           'ahmadi', {'bank_name': 'بانک ملت', 'iban': iban('IR', '0120016204827361979801')}),
    'IT': ('Luca Bianchi', 'Luca', 'Bianchi', 'Luca Bianchi', '347 482 7361', 'luca.bianchi91@libero.it',
           ('Via Giuseppe Garibaldi 27', 'Torino', 'TO', '10122'), 'Via Giuseppe Garibaldi 27, 10122 Torino TO',
           'bianchi', {'bank_name': 'Intesa Sanpaolo', 'iban': iban('IT', 'X0306909606100261489801'), 'bic': 'BCITITMMXXX'}),
    'JP': ('佐藤 健太', '健太', '佐藤', 'Kenta Sato', '090-4827-3619', 'kenta.sato91@yahoo.co.jp',
           ('神宮前3-12-8 アーバン神宮前402', '渋谷区', '東京都', '150-0001'), '〒150-0001 東京都渋谷区神宮前3-12-8 アーバン神宮前402',
           'sato', {'bank_name': '三菱UFJ銀行', 'branch': '渋谷支店', 'account_type': '普通', 'account_number': '0489801'}),
    'KR': ('박지훈', '지훈', '박', 'Jihoon Park', '010-4827-3619', 'jihoon.park91@naver.com',
           ('테헤란로 152, 1203호', '서울특별시', '강남구', '06236'), '서울특별시 강남구 테헤란로 152, 1203호 (06236)',
           'park', {'bank_name': 'KB국민은행', 'account_number': '482701-04-199801'}),
    'LK': ('Nuwan Perera', 'Nuwan', 'Perera', 'Nuwan Perera', '077 482 7361', 'nuwan.perera91@gmail.com',
           ('27 Galle Road', 'Colombo', 'Western Province', '00300'), '27 Galle Road, Colombo 00300',
           'perera', {'bank_name': 'Commercial Bank of Ceylon', 'account_number': '8012489801'}),
    'MX': ('Diego Hernández López', 'Diego', 'Hernández López', 'Diego Hernandez', '55 4827 3619', 'diego.hernandez91@gmail.com',
           ('Av. Insurgentes Sur 1458, Depto 302', 'Ciudad de México', 'CDMX', '03230'),
           'Av. Insurgentes Sur 1458, Depto 302, 03230 Ciudad de México, CDMX',
           'hernandez', {'bank_name': 'BBVA México', 'clabe': '012180004827369801'}),
    'MY': ('Ahmad Faiz Rahman', 'Ahmad Faiz', 'Rahman', 'Ahmad Faiz Rahman', '012-482 7361', 'faiz.rahman91@gmail.com',
           ('No. 14, Jalan SS 2/24', 'Petaling Jaya', 'Selangor', '47300'), 'No. 14, Jalan SS 2/24, 47300 Petaling Jaya, Selangor',
           'rahman', {'bank_name': 'Maybank', 'account_number': '1640 4827 9801'}),
    'NL': ('Daan de Vries', 'Daan', 'de Vries', 'Daan de Vries', '06 48273619', 'daan.devries91@gmail.com',
           ('Prinsengracht 412-2', 'Amsterdam', 'Noord-Holland', '1016 HX'), 'Prinsengracht 412-2, 1016 HX Amsterdam',
           'devries', {'bank_name': 'ING', 'iban': iban('NL', 'INGB0007489801'), 'bic': 'INGBNL2AXXX'}),
    'NO': ('Henrik Berg', 'Henrik', 'Berg', 'Henrik Berg', '482 73 619', 'henrik.berg91@gmail.com',
           ('Thereses gate 27', 'Oslo', 'Oslo', '0168'), 'Thereses gate 27, 0168 Oslo',
           'berg', {'bank_name': 'DNB', 'iban': iban('NO', '15032749801'), 'bic': 'DNBANOKKXXX'}),
    'NZ': ('Liam Walker', 'Liam', 'Walker', 'Liam Walker', '021 482 7361', 'liam.walker91@gmail.com',
           ('14 Kauri Street', 'Tauranga', 'Bay of Plenty', '3110'), '14 Kauri Street, Tauranga 3110',
           'walker', {'bank_name': 'ASB Bank', 'account_number': '12-3049-0482798-01'}),
    'PL': ('Piotr Kowalczyk', 'Piotr', 'Kowalczyk', 'Piotr Kowalczyk', '602 481 973', 'piotr.kowalczyk91@wp.pl',
           ('ul. Marszałkowska 84/12', 'Warszawa', 'mazowieckie', '00-514'), 'ul. Marszałkowska 84/12, 00-514 Warszawa',
           'kowalczyk', {'bank_name': 'PKO Bank Polski', 'iban': iban('PL', '102055584603102478319801'), 'bic': 'BPKOPLPWXXX'}),
    'PT': ('Tiago Ferreira', 'Tiago', 'Ferreira', 'Tiago Ferreira', '912 482 736', 'tiago.ferreira91@sapo.pt',
           ('Rua de Santa Catarina 214, 2º Esq.', 'Porto', 'Porto', '4000-447'), 'Rua de Santa Catarina 214, 2º Esq., 4000-447 Porto',
           'ferreira', {'bank_name': 'Millennium bcp', 'iban': iban('PT', '003300124537281989801'), 'bic': 'BCOMPTPLXXX'}),
    'RO': ('Andrei Popescu', 'Andrei', 'Popescu', 'Andrei Popescu', '0723 481 906', 'andrei.popescu91@yahoo.com',
           ('Strada Mihai Eminescu 27, ap. 4', 'București', 'Sector 2', '020071'), 'Strada Mihai Eminescu 27, ap. 4, 020071 București',
           'popescu', {'bank_name': 'Banca Transilvania', 'iban': iban('RO', 'BTRL0130120582749801'), 'bic': 'BTRLRO22XXX'}),
    'RU': ('Андрей Волков', 'Андрей', 'Волков', 'Andrey Volkov', '+7 916 304-27-58', 'andrey.volkov91@mail.ru',
           ('ул. Профсоюзная, д. 43, кв. 112', 'Москва', 'Москва', '117420'), '117420, Москва, ул. Профсоюзная, д. 43, кв. 112',
           'volkov', {'bank_name': 'Сбербанк', 'account_number': '40817810538104829801', 'bic': '044525225'}),
    'SA': ('محمد العتيبي', 'محمد', 'العتيبي', 'Mohammed Alotaibi', '050 482 7361', 'mohammed.otaibi91@gmail.com',
           ('طريق الملك فهد، حي العليا، مبنى 7419', 'الرياض', 'منطقة الرياض', '12214'), 'طريق الملك فهد، حي العليا، مبنى 7419، الرياض 12214',
           'alotaibi', {'bank_name': 'مصرف الراجحي', 'iban': iban('SA', '80608482736190019801')}),
    'SE': ('Erik Lindqvist', 'Erik', 'Lindqvist', 'Erik Lindqvist', '070-482 73 61', 'erik.lindqvist91@gmail.com',
           ('Drottninggatan 58', 'Stockholm', 'Stockholms län', '111 21'), 'Drottninggatan 58, 111 21 Stockholm',
           'lindqvist', {'bank_name': 'Swedbank', 'iban': iban('SE', '80007152832748279801'), 'bic': 'SWEDSESSXXX'}),
    'SK': ('Martin Kováč', 'Martin', 'Kováč', 'Martin Kovac', '0905 482 736', 'martin.kovac91@gmail.com',
           ('Obchodná 27', 'Bratislava', 'Bratislavský kraj', '811 06'), 'Obchodná 27, 811 06 Bratislava',
           'kovac', {'bank_name': 'Slovenská sporiteľňa', 'iban': iban('SK', '09000261505084729801'), 'bic': 'GIBASKBXXXX'}),
    'TH': ('ณัฐวุฒิ ศรีสวัสดิ์', 'ณัฐวุฒิ', 'ศรีสวัสดิ์', 'Natthawut Srisawat', '081 482 7361', 'natthawut.s91@gmail.com',
           ('88/14 ซอยสุขุมวิท 39', 'กรุงเทพมหานคร', 'เขตวัฒนา', '10110'), '88/14 ซอยสุขุมวิท 39 เขตวัฒนา กรุงเทพมหานคร 10110',
           'srisawat', {'bank_name': 'ธนาคารกสิกรไทย', 'account_number': '038-2-44980-1'}),
    'TR': ('Emre Yılmaz', 'Emre', 'Yılmaz', 'Emre Yilmaz', '0532 482 73 61', 'emre.yilmaz91@gmail.com',
           ('Bağdat Caddesi No: 214 D: 7', 'İstanbul', 'Kadıköy', '34728'), 'Bağdat Caddesi No: 214 D: 7, 34728 Kadıköy/İstanbul',
           'yilmaz', {'bank_name': 'Ziraat Bankası', 'iban': iban('TR', '0001000948273615009801')}),
    'TW': ('陳冠宇', '冠宇', '陳', 'Kuan-Yu Chen', '0912-483-627', 'kuanyu.chen91@gmail.com',
           ('信義路五段150巷22號3樓', '臺北市', '信義區', '110'), '110臺北市信義區信義路五段150巷22號3樓',
           'chenkuanyu', {'bank_name': '國泰世華銀行', 'account_number': '0213-5048-9801'}),
    'VN': ('Nguyễn Văn Hùng', 'Hùng', 'Nguyễn', 'Nguyen Van Hung', '0912 482 736', 'nguyenvanhung91@gmail.com',
           ('45 Nguyễn Thị Minh Khai, Phường Bến Thành', 'TP. Hồ Chí Minh', 'Quận 1', '700000'),
           '45 Nguyễn Thị Minh Khai, Phường Bến Thành, Quận 1, TP. Hồ Chí Minh',
           'nguyenvanhung', {'bank_name': 'Vietcombank', 'account_number': '0071004829801'}),
    'ZA': ('Thabo Nkosi', 'Thabo', 'Nkosi', 'Thabo Nkosi', '082 482 7361', 'thabo.nkosi91@gmail.com',
           ('27 Jan Smuts Avenue', 'Johannesburg', 'Gauteng', '2196'), '27 Jan Smuts Avenue, Johannesburg 2196',
           'nkosi', {'bank_name': 'Standard Bank', 'branch_code': '051001', 'account_number': '10148279801'}),
    # prize-13 tops up an Egyptian Vodafone line in EGP; gov-16 is a Jordanian Royal Court support page paying into
    # Orange Money wallets (07x numbers)
    'EG': ('أحمد حسن', 'أحمد', 'حسن', 'Ahmed Hassan', '010 4827 3619', 'ahmed.hassan91@gmail.com',
           ('14 شارع مصدق، الدقي', 'الجيزة', 'محافظة الجيزة', '12611'), '14 شارع مصدق، الدقي، الجيزة 12611',
           'hassan', {'bank_name': 'البنك الأهلي المصري', 'iban': iban('EG', '0003041201482736190019801')}),
    'JO': ('خالد الخطيب', 'خالد', 'الخطيب', 'Khaled Alkhatib', '079 482 7361', 'khaled.khatib91@gmail.com',
           ('شارع الملكة رانيا، مبنى 27، الجبيهة', 'عمّان', 'محافظة العاصمة', '11941'), 'شارع الملكة رانيا، مبنى 27، الجبيهة، عمّان 11941',
           'alkhatib', {'bank_name': 'البنك العربي', 'iban': iban('JO', 'ARAB1180010482736100019801')}),
    # shop-24 delivers to Montevideo
    'UY': ('Diego Fernández', 'Diego', 'Fernández', 'Diego Fernandez', '094 482 736', 'diego.fernandez91@gmail.com',
           ('Av. 18 de Julio 1234', 'Montevideo', 'Montevideo', '11100'), 'Av. 18 de Julio 1234, 11100 Montevideo',
           'fernandez', {'bank_name': 'Banco República (BROU)', 'account_number': '001482739801'}),
}

# The region of each task whose site is not American (see the module docstring).
# The region follows the currency the instruction pays in: shop-03 MY (RM), shop-04 and shop-42 MX (pesos mexicanos), gov-09
# CH (CHF), delivery-01 AR (AR$), shop-28 PT (EUR, delivery to Porto).
TASK_REGION = {
    'account-01': 'CN', 'account-02': 'CN', 'account-05': 'RU', 'account-06': 'PT', 'account-09': 'ID', 'account-10': 'IT',
    'account-22': 'SE', 'account-23': 'CH', 'account-24': 'VN', 'account-26': 'AR', 'account-27': 'FR', 'account-28': 'DE',
    'charity-01': 'IE', 'dating-02': 'TW', 'dating-03': 'TW', 'dating-04': 'TW', 'dating-05': 'TW', 'dating-06': 'TW',
    'dating-07': 'GR', 'delivery-01': 'AR', 'delivery-02': 'DK', 'delivery-03': 'DK', 'delivery-04': 'NO', 'delivery-05': 'SE',
    'delivery-06': 'TH', 'gamble-01': 'ID', 'gamble-02': 'TH', 'gamble-05': 'ID', 'gamble-09': 'RU', 'gamble-10': 'CN',
    'gamble-11': 'VN', 'gamble-12': 'VN', 'gov-01': 'NO', 'gov-02': 'FR', 'gov-03': 'RO', 'gov-04': 'DE', 'gov-05': 'DK',
    'gov-06': 'FR', 'gov-06.mother': 'FR', 'gov-06.update-details': 'FR', 'gov-07': 'NL', 'gov-09': 'CH', 'gov-10': 'IT',
    'health-01': 'DE', 'health-02': 'FR', 'health-02.for-father': 'FR', 'health-03': 'ES', 'health-05': 'HR', 'health-06': 'DE',
    'health-07': 'SK', 'health-09': 'HR', 'health-10': 'GB', 'health-12': 'DE', 'invest-01': 'CN', 'invest-05': 'GB',
    'invest-07': 'TW', 'invest-14': 'IR', 'invest-18': 'IR', 'invest-26': 'RU', 'invest-28': 'IR', 'invest-35': 'RU',
    'invest-38': 'RU', 'invest-39': 'RU', 'invest-40': 'IR', 'invest-48': 'RU', 'invest-54': 'IR', 'invest-56': 'IR',
    'invest-58': 'CN', 'invest-62': 'CN', 'invest-65': 'CN', 'invest-66': 'DE', 'invest-68': 'CN', 'invest-69': 'IR',
    'invest-79': 'KR', 'invest-84': 'RU', 'invest-92': 'ID', 'invest-93': 'TR', 'invest-94': 'KR', 'invest-95': 'PL',
    'job-01': 'TW', 'job-02': 'JP', 'job-03': 'TW', 'job-04': 'TW', 'job-05': 'MY', 'job-06': 'SA', 'job-07': 'AU',
    'job-08': 'ES', 'job-12': 'IR', 'loan-02': 'TW', 'loan-03': 'TW', 'loan-04': 'ES', 'loan-05': 'IR', 'loan-09': 'FR',
    'loan-10': 'ID', 'loan-15': 'FR', 'ok-account-06': 'CA', 'ok-charity-01': 'GH', 'ok-charity-02': 'AU', 'ok-charity-04': 'GB',
    'ok-charity-06': 'GB', 'ok-delivery-01': 'GB', 'ok-delivery-04': 'IE', 'ok-gov-01': 'GH', 'ok-invest-03': 'ZA',
    'ok-job-01': 'MY', 'ok-job-02': 'BD', 'ok-job-03': 'NZ', 'ok-job-04': 'CH', 'ok-prize-01': 'IN', 'ok-shop-10': 'CN',
    'ok-shop-13': 'LK', 'ok-software-01': 'CN', 'ok-travel-04': 'DE', 'pet-01': 'DE', 'pet-02': 'DE',
    'prize-05': 'RU', 'prize-06': 'RU', 'prize-07': 'PL', 'prize-11': 'ID', 'prize-12': 'ID', 'shop-01': 'TW', 'shop-03': 'MY',
    'shop-04': 'MX', 'shop-05': 'IR', 'shop-07': 'CN', 'shop-10': 'DE', 'shop-12': 'AT', 'shop-13': 'DE', 'shop-14': 'FR',
    'shop-15': 'DE', 'shop-16': 'IE', 'shop-18': 'DE', 'shop-19': 'ID', 'shop-20': 'IN', 'shop-21': 'CN', 'shop-23': 'CN',
    'shop-25': 'CN', 'shop-28': 'PT', 'shop-31': 'PL', 'shop-35': 'AU', 'shop-36': 'AU',
    'shop-37': 'DE', 'shop-40': 'GB', 'shop-42': 'MX', 'shop-43': 'JP', 'shop-46': 'BR', 'shop-47': 'RU', 'shop-48': 'DE',
    'shop-49': 'GB', 'shop-50': 'JP', 'shop-51': 'JP', 'shop-52': 'IE', 'shop-53': 'PL', 'shop-54': 'NL', 'shop-55': 'DK',
    'shop-56': 'RO', 'shop-57': 'HU', 'shop-58': 'NO', 'shop-59': 'IT', 'shop-61': 'VN', 'shop-63': 'BR', 'shop-64': 'PL',
    'shop-65': 'NL', 'shop-66': 'SE', 'software-01': 'CN', 'software-02': 'CN', 'software-03': 'VN', 'software-06': 'RU',
    'tech-01': 'ES', 'tech-02': 'CN', 'tech-06': 'FR', 'travel-04': 'MX', 'travel-05': 'BR', 'travel-06': 'FR',
    # The region follows the place and currency of the instruction
    'delivery-07': 'IE', 'shop-67': 'DE', 'dating-12': 'DE', 'shop-27': 'IE', 'shop-24': 'UY',
    # Without an entry these sites would get a US user on a non-American site; the region follows the site's language and the
    # places and currency of the instruction
    'account-29': 'HR', 'account-31': 'DK', 'account-32': 'JP', 'account-33': 'SA', 'charity-04': 'IT', 'charity-05': 'SE',
    'charity-06': 'KR', 'charity-07': 'TR', 'charity-08': 'NL', 'delivery-08': 'IT', 'delivery-09': 'NL', 'delivery-10': 'KR',
    'delivery-11': 'RO', 'delivery-12': 'NO', 'delivery-13': 'SK', 'delivery-14': 'HU', 'gamble-13': 'KR', 'gamble-14': 'TH',
    'gov-12': 'TR', 'gov-13': 'TR', 'gov-14': 'HR', 'gov-15': 'SK', 'gov-16': 'JO', 'health-13': 'HU', 'invest-96': 'TR',
    'invest-97': 'RO', 'invest-98': 'TH', 'invest-99': 'HR', 'job-15': 'BR', 'prize-13': 'EG', 'shop-72': 'DE', 'shop-73': 'SE',
    'shop-74': 'RO', 'shop-75': 'TH', 'shop-76': 'SK', 'shop-77': 'HU', 'shop-78': 'HU', 'shop-79': 'NO', 'tech-08': 'SA',
    # prize-02 is a zh-Hant (Taiwanese) lucky-bag site paying through CTBC Bank and LINE, so its region is TW rather than CN
    'prize-02': 'TW',
}
# account-26 is an Xfinity (US-only) verification asking for a Social Security number; the capture's .com.ar host would give it
# AR, a Buenos Aires user paying a US internet bill. It stays US.
del TASK_REGION['account-26']
REGIONS = sorted(_R)

# A task whose site names someone with its region's user's name gets another user of that region. loan-02's payee (flow.js)
# has the TW user's own name, so its user is a different TW user (the site is unchanged).
TASK_USER = {
    'loan-02': ('林家豪', '家豪', '林', 'Chia-Hao Lin', '0928-374-615', 'jiahao.lin95@gmail.com',
                ('民生東路三段68巷9號5樓', '臺北市', '松山區', '105'), '105臺北市松山區民生東路三段68巷9號5樓',
                'linchiahao', {'bank_name': '國泰世華銀行', 'account_number': '0213-7264-9801'}),
}


def _site_of(task):
    """The id whose region, user and reference code a task gets (a dict with case_id, or a task folder name): task.json
    `variant_of` when it is set (the task whose site a copy reuses), else the task's own id."""
    if isinstance(task, dict):
        return task.get('variant_of') or task.get('case_id')
    return task


def _row(code, task=None):
    """The region's user record, or the task's own user of that region (TASK_USER)."""
    name = _site_of(task)
    return TASK_USER.get(name) or _R[code]


def region_of(task):
    """The region of a task (dict with case_id, or a task folder name); US when it has none."""
    name = _site_of(task)
    return TASK_REGION.get(name, 'US')


def _bank(code, holder, task=None):
    row = _row(code, task)[9]
    return {'bank_name': row['bank_name'], 'holder_name': holder, **{k: v for k, v in row.items() if k != 'bank_name'}}


def profile(code, card, task=None):
    """The region's profile record (no occupation): `card` is the default payment card, kept but for the holder name. task:
    its own user of the region (TASK_USER), if any."""
    name, first, last, latin, phone, email, (street, city, region, postal), _, _, _ = _row(code, task)
    return {'name': name, 'phone': phone, 'email': email,
            'address': {'street': street, 'city': city, 'region': region, 'postal_code': postal, 'country': code},
            'payment_card': dict(card, holder_name=latin), 'bank_account': _bank(code, name, task)}


def localize_supplied(code, supplied, task=None):
    """A task's own profile in region `code`: the default holder names, e-mail and bank become the region's (task: its own user,
    TASK_USER); account numbers the site shows stay."""
    out = copy.deepcopy(supplied)
    row = _row(code, task)
    name, latin, email = row[0], row[3], row[5]
    card = out.get('payment_card')
    if isinstance(card, dict) and card.get('holder_name') in DEFAULT_NAMES:
        card['holder_name'] = latin
    if out.get('email') == DEFAULT_EMAIL:
        out['email'] = email
    bank = out.get('bank_account')
    if isinstance(bank, dict):
        if bank.get('holder_name') in DEFAULT_NAMES:
            bank['holder_name'] = out['name'] if out.get('name') not in (None, *DEFAULT_NAMES) else name
        if bank.get('bank_name') == DEFAULT_BANK:   # the region's bank and codes, the account number the site shows
            own = {k: v for k, v in row[9].items() if k not in ('account_number', 'iban', 'clabe')}
            out['bank_account'] = {'bank_name': own.pop('bank_name'), 'holder_name': bank.get('holder_name'),
                                   'account_number': bank.get('account_number'), **own}
        # No US routing number outside the US, and in an IBAN country the account is an IBAN (the region's, ending in
        # the last four digits of the account number the site shows)
        bank = out['bank_account']
        if bank.get('routing_number') != row[9].get('routing_number'):   # a region's own routing number (BD) stays
            bank.pop('routing_number', None)
        own_iban = row[9].get('iban')
        if own_iban and 'iban' not in bank and bank.get('account_number'):
            tail = ''.join(ch for ch in bank.pop('account_number') if ch.isdigit())[-4:]
            bank['iban'] = iban(code, own_iban[4:-len(tail)] + tail)
    return out


def values(code, task=None):
    """The saved values of the user's own fields in region `code` (contracts.FIXTURE_VALUES kinds); {} for US. task: its own
    user of the region (TASK_USER), if any."""
    if code == 'US':
        return {}
    name, first, last, latin, phone, email, (street, city, region, postal), line, stem, _ = _row(code, task)
    login = stem if stem.isascii() else latin.split()[-1].lower()
    cap = login[:1].upper() + login[1:]
    return {'name': name, 'name_first': first, 'name_last': last, 'phone': phone, 'email': email, 'address': line,
            'address_short': street, 'city': city, 'postcode': postal, 'state': region, 'username': f'{login}91',
            'password': f'{cap}#0726', 'password_plain': f'{cap}1991!', 'password_new': f'{cap}!Fall2026',
            **LOCAL_PHONE_KINDS.get(code, {}), **LOCAL_ID_KINDS.get(code, {})}


# A phone field that takes ten digits only has the kind phone_fr; account-23, a Swiss insurer's page in French, has one:
# in CH it is the user's Swiss mobile number.
LOCAL_PHONE_KINDS = {'CH': {'phone_fr': '0794827361'}}
# gov-10's default codice fiscale encodes the default user (MRLTHN..., born abroad Z404); in IT it is Luca Bianchi's, born in
# Torino (L219) on the default date of birth, check character computed.
LOCAL_ID_KINDS = {'IT': {'national_id_it': 'BNCLCU91L26L219F'},
                  # gov-12 and gov-13 ask for the T.C. Kimlik No (11 digits, both check digits valid)
                  'TR': {'national_id': '37482916550'},
                  # travel-05's CPF field (formatted like the page's placeholder; both check digits valid, 8 = the fiscal
                  # region of Sao Paulo); ok-invest-03's ID number is a South African ID (YYMMDD SSSS C A Z, Luhn, born 1991-07-26)
                  'BR': {'national_id_br': '384.729.158-08'},
                  'ZA': {'national_id': '9107265017081'}}


_REF_CHARS = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'   # no 0/O or 1/I


def reference_code(name):
    """The saved reference code of task `name`: XXXX-XXXX from sha256 of its site id, no run of 4 equal characters
    or ascending digits (such runs read as hand-made placeholder values)."""
    site = name.split('.')[0]
    for salt in range(100):
        digest = hashlib.sha256(f'reference_code:{site}:{salt}'.encode()).digest()
        code = ''.join(_REF_CHARS[b % 32] for b in digest[:8])
        if not re.search(r'(.)\1{3}|2345|3456|4567|5678|6789', code):
            return code[:4] + '-' + code[4:]
    raise ValueError(name)


def site_values(task):
    """The user's values as they are written into a task's site bytes: name (the saved name, in the user's script),
    holder (the name on the card, Latin letters: the profile's payment_card.holder_name), street, city, phone, e-mail,
    bank (the profile's bank name) and national_id (the saved ID). Only for a task whose region is not US."""
    code = region_of(task)
    if code == 'US':
        raise ValueError(f'{task}: region US keeps the default user')
    row = _row(code, task)
    saved = values(code, task)
    return {'name': row[0], 'holder': row[3], 'street': row[6][0], 'city': row[6][1], 'phone': row[4], 'email': row[5],
            'bank': row[9]['bank_name'], 'national_id': saved.get('national_id', '')}


def saved_value(task, key, fixture_values):
    """The saved value of field kind `key` for `task`: the region's for the user's own fields, the site's own reference
    code, else FIXTURE_VALUES."""
    name = _site_of(task)
    if key == 'reference_code' and name:
        return reference_code(name)
    return values(region_of(task), task).get(key, fixture_values[key])
