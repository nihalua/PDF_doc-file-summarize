from docsum.details import find_details
from docsum.textproc import blocks, detect_language, lower, split_sentences, stem, words


def test_detect_language():
    assert detect_language("The tenant shall pay the rent on the first day of each month.") == "en"
    assert detect_language("Kiracı, kira bedelini her ayın ilk günü ödemekle yükümlüdür.") == "tr"


def test_turkish_lowercase_and_apostrophes():
    assert lower("İSTANBUL IRMAK", "tr") == "istanbul ırmak"
    assert words("Türkiye'nin başkenti Ankara'dır.", "tr") == ["türkiye", "başkenti", "ankara"]


def test_stemming_groups_word_forms():
    assert stem("sözleşmenin", "tr") == stem("sözleşme", "tr")
    assert stem("employees", "en") == stem("employee", "en")
    assert stem("requirements", "en") == stem("requirement", "en")


def test_sentence_split_respects_abbreviations():
    en = split_sentences("Dr. Smith met Mr. J. Doe at 10 a.m. today. They signed the contract. Done!", "en")
    assert en == ["Dr. Smith met Mr. J. Doe at 10 a.m. today.", "They signed the contract.", "Done!"]
    tr = split_sentences("Ödeme her ayın 5. günü yapılır. Prof. Dr. Ayşe Kaya vb. kişiler katılır. Bitti.", "tr")
    assert tr == ["Ödeme her ayın 5. günü yapılır.", "Prof. Dr. Ayşe Kaya vb. kişiler katılır.", "Bitti."]


def test_blocks_join_wrapped_lines_and_find_headings():
    text = (
        "MADDE 2 – AMAÇ\n"
        "Bu sözleşmenin amacı, No: 15 Daire:\n"
        "8 adresinde bulunan konutun kira-\n"
        "lanmasıdır.\n"
        "1. Introduction\n"
        "The purpose is simple."
    )
    got = [(b.kind, b.text) for b in blocks(text)]
    assert got == [
        ("heading", "MADDE 2 – AMAÇ"),
        ("text", "Bu sözleşmenin amacı, No: 15 Daire: 8 adresinde bulunan konutun kiralanmasıdır."),
        ("heading", "1. Introduction"),
        ("text", "The purpose is simple."),
    ]


def test_find_details():
    assert find_details(
        "The Tenant shall pay 12,500 TL per month from 1 January 2027, within 30 days of invoice (Article 5.2)."
    ) == [("amount", "12,500 TL"), ("date", "1 January 2027"), ("time_limit", "within 30 days"),
          ("reference", "Article 5.2")]
    assert find_details("Artış oranı %25 ile sınırlıdır; en geç 15 gün içinde 01.02.2027 tarihine kadar ödenir.") == [
        ("percentage", "%25"), ("time_limit", "en geç 15 gün içinde"), ("date", "01.02.2027")]
    assert find_details("5 bin kişi katıldı ve 2 milyon TL toplandı.") == [("amount", "2 milyon TL")]
