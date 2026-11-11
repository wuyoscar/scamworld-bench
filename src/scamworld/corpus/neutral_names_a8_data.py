"""Data tables of the second stage of the neutral-name rules (scamworld.corpus.neutral_names).

MESSAGES   what a normal site says when an action failed / was already submitted / has required fields empty, per page
           language (index 0 failed, 1 duplicate, 2 missing). The page runtime picks the row from <html lang>, or from the
           script of the visible text when the page declares no usable language; English otherwise.
Builder comments and the flow.js annotation payloads are not handled here (src/scamworld/corpus/annotations_a8.py).
"""

MESSAGES = {
    'en': ('Something went wrong. Please try again.', 'This has already been submitted.', 'Please complete the required fields.'),
    'zh': ('出了点问题，请重试。', '该内容已提交，请勿重复提交。', '请填写所有必填项。'),
    'zt': ('發生錯誤，請再試一次。', '此內容已提交，請勿重複提交。', '請填寫所有必填欄位。'),
    'ja': ('問題が発生しました。もう一度お試しください。', 'すでに送信済みです。', '必須項目をすべて入力してください。'),
    'ko': ('문제가 발생했습니다. 다시 시도해 주세요.', '이미 제출되었습니다.', '필수 항목을 모두 입력해 주세요.'),
    'de': ('Etwas ist schiefgelaufen. Bitte versuchen Sie es erneut.', 'Dies wurde bereits übermittelt.', 'Bitte füllen Sie alle Pflichtfelder aus.'),
    'fr': ('Une erreur s’est produite. Veuillez réessayer.', 'Ceci a déjà été envoyé.', 'Veuillez remplir tous les champs obligatoires.'),
    'es': ('Algo salió mal. Inténtalo de nuevo.', 'Esto ya se ha enviado.', 'Completa los campos obligatorios.'),
    'pt': ('Algo deu errado. Tente novamente.', 'Isto já foi enviado.', 'Preencha os campos obrigatórios.'),
    'it': ('Qualcosa è andato storto. Riprova.', 'Questo è già stato inviato.', 'Compila tutti i campi obbligatori.'),
    'nl': ('Er is iets misgegaan. Probeer het opnieuw.', 'Dit is al verzonden.', 'Vul alle verplichte velden in.'),
    'ru': ('Что-то пошло не так. Попробуйте ещё раз.', 'Это уже отправлено.', 'Заполните все обязательные поля.'),
    'bg': ('Нещо се обърка. Опитайте отново.', 'Това вече е изпратено.', 'Моля, попълнете всички задължителни полета.'),
    'pl': ('Coś poszło nie tak. Spróbuj ponownie.', 'To zostało już wysłane.', 'Wypełnij wszystkie wymagane pola.'),
    'tr': ('Bir şeyler ters gitti. Lütfen tekrar deneyin.', 'Bu zaten gönderildi.', 'Lütfen zorunlu alanları doldurun.'),
    'vi': ('Đã xảy ra lỗi. Vui lòng thử lại.', 'Nội dung này đã được gửi.', 'Vui lòng điền đầy đủ các trường bắt buộc.'),
    'id': ('Terjadi kesalahan. Silakan coba lagi.', 'Ini sudah dikirim.', 'Harap lengkapi semua kolom yang wajib diisi.'),
    'th': ('เกิดข้อผิดพลาด โปรดลองอีกครั้ง', 'ส่งข้อมูลนี้ไปแล้ว', 'โปรดกรอกข้อมูลที่จำเป็นให้ครบ'),
    'fa': ('مشکلی پیش آمد. لطفاً دوباره تلاش کنید.', 'این مورد قبلاً ارسال شده است.', 'لطفاً همه فیلدهای الزامی را پر کنید.'),
    'sv': ('Något gick fel. Försök igen.', 'Detta har redan skickats.', 'Fyll i alla obligatoriska fält.'),
    'da': ('Noget gik galt. Prøv igen.', 'Dette er allerede sendt.', 'Udfyld alle obligatoriske felter.'),
    'no': ('Noe gikk galt. Prøv igjen.', 'Dette er allerede sendt.', 'Fyll ut alle obligatoriske felt.'),
    'hr': ('Nešto je pošlo po zlu. Pokušajte ponovno.', 'Ovo je već poslano.', 'Ispunite sva obavezna polja.'),
    'sk': ('Niečo sa pokazilo. Skúste to znova.', 'Toto už bolo odoslané.', 'Vyplňte všetky povinné polia.'),
    'ro': ('Ceva nu a funcționat. Încearcă din nou.', 'Acesta a fost deja trimis.', 'Completează toate câmpurile obligatorii.'),
    'hu': ('Hiba történt. Kérjük, próbálja újra.', 'Ez már el lett küldve.', 'Kérjük, töltse ki a kötelező mezőket.'),
}
