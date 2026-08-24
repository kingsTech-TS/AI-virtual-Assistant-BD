import pytest
from app.constants.intents import Intent
from app.models.knowledge import new_knowledge_doc
from app.services.chunking_service import ChunkingService, get_chunking_service
from app.services.intent_service import get_intent_service
from app.services.reranking_service import get_reranking_service
from app.services.retrieval_service import get_retrieval_service


@pytest.fixture
def seeded_kb():
    """Mock in-memory knowledge chunks matching seed documents."""
    return [
        new_knowledge_doc(
            title="Course Registration Guide",
            section="Missing Courses",
            category="course_registration",
            intent=["course_missing", "course_not_available"],
            source="Academic Regulations Handbook 2026",
            page=5,
            content=(
                "A course may be missing from a student's course list because the course is not offered in the current "
                "semester, the student has not met a prerequisite, the course is not part of the student's approved curriculum, "
                "or the department has not made the course available for registration. If you believe a course like CSC 301 should "
                "be available, check your approved curriculum and consult your departmental course adviser."
            ),
        ),
        new_knowledge_doc(
            title="Course Registration Guide",
            section="Course Prerequisites",
            category="course_registration",
            intent=["course_prerequisite"],
            source="Academic Regulations Handbook 2026",
            page=6,
            content=(
                "Students cannot register for advanced modules without satisfying prerequisite requirements. "
                "For example, CSC 301 (Database Systems) strictly requires completion of CSC 201 (Data Structures). "
                "Prerequisite waivers require explicit written approval from the Head of Department (HOD)."
            ),
        ),
        new_knowledge_doc(
            title="Examination Committee Regulations",
            section="Semester Examination Guidelines",
            category="exam_schedule",
            intent=["examination", "exam_schedule"],
            source="Demo Examination Committee Regulations",
            page=1,
            content=(
                "Students must arrive at the examination hall at least 30 minutes before the scheduled start time. "
                "A valid Student Identity Card and a stamped Examination Docket are mandatory for entry."
            ),
        ),
        new_knowledge_doc(
            title="Student Fees and Bursary Schedule",
            section="Fee Payment Guidelines",
            category="fees",
            intent=["fees"],
            source="Demo Bursary Department",
            page=1,
            content=(
                "Tuition fees must be paid through the official payment gateway integrated into the student portal. "
                "Generate a Payment Reference Number (Remita/RRR) on the portal before initiating payment."
            ),
        ),
    ]


@pytest.mark.asyncio
async def test_semantic_intent_variations():
    """Requirement 1 & 32: All semantic variations of missing course queries must classify to course_missing."""
    service = get_intent_service()
    
    variations = [
        "Why is there course missing from my list?",
        "Why can't I see CSC 301?",
        "One of my courses isn't showing.",
        "I can't find a course on my portal.",
        "Why is CSC301 not available?",
        "The course I want isn't listed.",
        "A course disappeared from my registration page.",
        "Why isn't this subject showing?",
        "I don't have one of my courses.",
        "Why can't I register for this course?",
    ]

    for q in variations:
        result = await service.classify(q)
        assert result.category == "course_registration", f"Failed category for: {q}"
        assert result.intent in (
            Intent.COURSE_MISSING.value,
            Intent.COURSE_NOT_AVAILABLE.value,
            Intent.COURSE_REGISTRATION.value,
        ), f"Failed intent for: {q} -> got {result.intent}"


@pytest.mark.asyncio
async def test_semantic_reranking_retrieves_missing_course_section(seeded_kb):
    """Requirement 11 & 32: Diverse phrasing must retrieve 'Course Registration Guide -> Missing Courses' as top chunk."""
    reranker = get_reranking_service()
    
    queries = [
        "Why is there course missing from my list?",
        "Why can't I see CSC 301?",
        "One of my courses isn't showing on the portal.",
        "A course disappeared from my registration page.",
    ]

    for q in queries:
        ranked_chunks, top_score, meets_thresh = reranker.rerank_chunks(
            query=q,
            chunks=seeded_kb,
            intent="course_missing",
            category="course_registration",
            top_k=3,
        )
        assert len(ranked_chunks) > 0
        top_chunk = ranked_chunks[0]
        assert top_chunk["title"] == "Course Registration Guide"
        assert top_chunk["section"] == "Missing Courses"
        assert meets_thresh is True, f"Failed confidence threshold for: {q}"


@pytest.mark.asyncio
async def test_exact_entity_matching_for_prerequisites(seeded_kb):
    """Requirement 12: Query asking about prerequisites for CSC 301 must retrieve Prerequisites section with high relevance."""
    reranker = get_reranking_service()
    query = "What are the prerequisites for CSC 301?"

    ranked_chunks, top_score, meets_thresh = reranker.rerank_chunks(
        query=query,
        chunks=seeded_kb,
        intent="course_prerequisite",
        category="course_registration",
        top_k=2,
    )
    assert len(ranked_chunks) > 0
    top_chunk = ranked_chunks[0]
    assert top_chunk["section"] == "Course Prerequisites"
    assert "CSC 301" in top_chunk["content"]


@pytest.mark.asyncio
async def test_negative_retrieval_discrimination(seeded_kb):
    """Requirement 33: Unrelated questions must NOT retrieve Missing Courses as the primary chunk."""
    reranker = get_reranking_service()

    # Exam inquiry
    ranked, _, _ = reranker.rerank_chunks(
        query="When is the examination date and timetable?",
        chunks=seeded_kb,
        intent="exam_schedule",
        category="exam_schedule",
        top_k=2,
    )
    assert ranked[0]["section"] != "Missing Courses"
    assert ranked[0]["section"] == "Semester Examination Guidelines"

    # Fee inquiry
    ranked_fee, _, _ = reranker.rerank_chunks(
        query="How do I pay my tuition fees and generate RRR?",
        chunks=seeded_kb,
        intent="fees",
        category="fees",
        top_k=2,
    )
    assert ranked_fee[0]["section"] != "Missing Courses"
    assert ranked_fee[0]["section"] == "Fee Payment Guidelines"


def test_chunking_service_section_preservation():
    """Requirement 4 & 5: Chunking service must detect section headers and retain section metadata."""
    chunker = ChunkingService(target_chunk_tokens=100, overlap_tokens=20)
    sample_text = (
        "# COURSE REGISTRATION\n\n"
        "Students must register online at the portal before resumption.\n\n"
        "## Missing Courses\n\n"
        "A course may be missing from a student course list because the prerequisite is unmet.\n\n"
        "## Course Prerequisites\n\n"
        "CSC 301 requires completion of CSC 201."
    )
    
    chunks = chunker.chunk_document(
        file_bytes=sample_text.encode("utf-8"),
        filename="handbook.txt",
        title="Student Handbook 2026",
        category="course_registration",
    )

    assert len(chunks) >= 2
    sections = [c["section"] for c in chunks]
    assert any("Missing Courses" in s for s in sections)
    assert any("Course Prerequisites" in s for s in sections)
    for c in chunks:
        assert c["title"] == "Student Handbook 2026"
        assert c["category"] == "course_registration"
