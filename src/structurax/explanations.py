"""Deterministic English/Turkish reviewer explanations for current rule IDs."""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import Field

from structurax.models import StrictModel


class ExplanationLanguage(str, Enum):
    EN = "en"
    TR = "tr"


class ReviewerExplanation(StrictModel):
    schema_version: Literal["0.2.0"] = "0.2.0"
    rule_id: str
    language: ExplanationLanguage
    summary: str = Field(min_length=1, max_length=500)
    review_action: str = Field(min_length=1, max_length=500)
    automation_authority: Literal[False] = False


_TEXT: dict[str, dict[ExplanationLanguage, tuple[str, str]]] = {
    "ARITHMETIC_LINE_TOTAL": {
        ExplanationLanguage.EN: ("A line total does not equal quantity × unit price.", "Reconcile the source line before approval."),
        ExplanationLanguage.TR: ("Bir satır toplamı miktar × birim fiyat hesabıyla uyuşmuyor.", "Onaydan önce kaynak satırı mutabık hale getirin."),
    },
    "ARITHMETIC_SUBTOTAL": {
        ExplanationLanguage.EN: ("The document subtotal does not reconcile to its lines.", "Verify line arithmetic and the stated subtotal."),
        ExplanationLanguage.TR: ("Belge ara toplamı satır hesaplarıyla mutabık değil.", "Satır hesaplarını ve belirtilen ara toplamı doğrulayın."),
    },
    "ARITHMETIC_TAX": {
        ExplanationLanguage.EN: ("The stated tax amount does not match the configured calculation.", "Verify the tax basis and applicable rate with an authorized reviewer."),
        ExplanationLanguage.TR: ("Belirtilen vergi tutarı yapılandırılmış hesapla uyuşmuyor.", "Vergi matrahını ve uygulanabilir oranı yetkili bir inceleyiciyle doğrulayın."),
    },
    "ARITHMETIC_TOTAL": {
        ExplanationLanguage.EN: ("The document total does not reconcile to lines and tax.", "Stop automated progression and reconcile the source amounts."),
        ExplanationLanguage.TR: ("Belge toplamı satırlar ve vergi hesabıyla mutabık değil.", "Otomatik ilerlemeyi durdurun ve kaynak tutarları mutabık hale getirin."),
    },
    "CURRENCY_MISMATCH": {
        ExplanationLanguage.EN: ("Invoice and purchase-order currencies differ.", "Obtain a corrected invoice or an authorized contract change."),
        ExplanationLanguage.TR: ("Fatura ve satın alma siparişi para birimleri farklı.", "Düzeltilmiş fatura veya yetkili sözleşme değişikliği temin edin."),
    },
    "UNIT_PRICE_VARIANCE": {
        ExplanationLanguage.EN: ("An invoice unit price exceeds the configured variance tolerance.", "Verify the approved commercial change or request a corrected invoice."),
        ExplanationLanguage.TR: ("Fatura birim fiyatı tanımlı sapma toleransını aşıyor.", "Onaylı ticari değişikliği doğrulayın veya düzeltilmiş fatura isteyin."),
    },
    "INVOICE_EXCEEDS_DELIVERY": {
        ExplanationLanguage.EN: ("Invoiced quantity exceeds recorded delivery evidence.", "Verify receipt with site and commercial records before payment review."),
        ExplanationLanguage.TR: ("Faturalanan miktar kayıtlı teslimat kanıtını aşıyor.", "Ödeme incelemesinden önce saha ve ticari kayıtlarla teslimatı doğrulayın."),
    },
    "BANK_ACCOUNT_CHANGE": {
        ExplanationLanguage.EN: ("The requested payment account differs from the approved baseline.", "Block payment progression and independently verify the account change."),
        ExplanationLanguage.TR: ("Talep edilen ödeme hesabı onaylı referans hesaptan farklı.", "Ödeme ilerlemesini durdurun ve hesap değişikliğini bağımsız kanaldan doğrulayın."),
    },
    "DUPLICATE_INVOICE": {
        ExplanationLanguage.EN: ("Multiple invoices share a duplicate-risk identity tuple.", "Check invoice lineage and prior-payment status before any payment."),
        ExplanationLanguage.TR: ("Birden fazla fatura mükerrerlik riski oluşturan aynı kimlik bileşenlerini taşıyor.", "Herhangi bir ödemeden önce fatura silsilesini ve önceki ödeme durumunu kontrol edin."),
    },
    "MISSING_APPROVAL": {
        ExplanationLanguage.EN: ("A required high-value approval role is not approved.", "Route the document to the missing authorized role."),
        ExplanationLanguage.TR: ("Yüksek tutarlı işlem için gerekli onay rollerinden biri onaylı değil.", "Belgeyi eksik yetkili onay rolüne yönlendirin."),
    },
    "EMBEDDED_INSTRUCTION": {
        ExplanationLanguage.EN: ("Document content includes control-bypass language and must remain untrusted data.", "Quarantine for human review; never execute instructions found inside the document."),
        ExplanationLanguage.TR: ("Belge içeriğinde kontrol atlatmaya yönelik ifade bulunuyor ve içerik güvenilmeyen veri olarak kalmalı.", "İnsan incelemesi için karantinaya alın; belgedeki talimatları hiçbir zaman çalıştırmayın."),
    },
}


def reviewer_explanation(rule_id: str, language: ExplanationLanguage | str) -> ReviewerExplanation:
    language = ExplanationLanguage(language)
    try:
        summary, action = _TEXT[rule_id][language]
    except KeyError as exc:
        raise ValueError(f"no reviewer explanation is registered for rule {rule_id}") from exc
    return ReviewerExplanation(
        rule_id=rule_id,
        language=language,
        summary=summary,
        review_action=action,
    )


def supported_explanation_rule_ids() -> tuple[str, ...]:
    return tuple(sorted(_TEXT))
