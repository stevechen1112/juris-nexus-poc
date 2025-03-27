"""
法律任務類型模組 - 提供各種法律任務的實現
"""

from app.legal_tasks.research_assistant import LegalResearchAssistant
from app.legal_tasks.document_drafter import LegalDocumentDrafter
from app.legal_tasks.litigation_helper import LitigationHelper
from app.legal_tasks.consultation_service import LegalConsultationService

__all__ = [
    'LegalResearchAssistant',
    'LegalDocumentDrafter',
    'LitigationHelper',
    'LegalConsultationService'
]
