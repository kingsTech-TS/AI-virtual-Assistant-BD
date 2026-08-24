#!/usr/bin/env python3
"""
Database Seeding Script.
Seeds demo departments, sample knowledge base documents with embeddings, and sample FAQs.
All seeded entries are explicitly marked as DEMO / SAMPLE data.
"""

from __future__ import annotations

import asyncio
import sys
from motor.motor_asyncio import AsyncIOMotorClient

from app.ai.embeddings import get_embeddings_provider
from app.constants.statuses import FAQStatus, KnowledgeStatus
from app.core.config import settings
from app.database.collections import DEPARTMENTS, FAQS, KNOWLEDGE_BASE
from app.models.department import new_department_doc
from app.models.faq import new_faq_doc
from app.models.knowledge import new_knowledge_doc
from app.utils.helpers import utcnow

DEMO_DEPARTMENTS = [
    {
        "name": "Computer Science",
        "code": "CSC",
        "faculty": "Physical Sciences",
        "description": "Department of Computer Science offering undergraduate and postgraduate degrees in Software, AI, and Systems.",
        "support_email": "csc-support@demo.institution.edu",
    },
    {
        "name": "Physics",
        "code": "PHY",
        "faculty": "Physical Sciences",
        "description": "Department of Physics offering pure and applied physics degrees.",
        "support_email": "phy-support@demo.institution.edu",
    },
    {
        "name": "Mathematics",
        "code": "MAT",
        "faculty": "Physical Sciences",
        "description": "Department of Mathematics offering pure mathematics, statistics, and computational modeling programs.",
        "support_email": "mat-support@demo.institution.edu",
    },
    {
        "name": "Chemistry",
        "code": "CHE",
        "faculty": "Physical Sciences",
        "description": "Department of Chemistry offering industrial and analytical chemistry courses.",
        "support_email": "che-support@demo.institution.edu",
    },
]

DEMO_KNOWLEDGE = [
    {
        "title": "[DEMO] Course Registration Procedure",
        "category": "course_registration",
        "source": "Demo Academic Handbook 2026",
        "content": (
            "To register for semester courses, log in to the Student Portal (portal.demo.institution.edu) "
            "using your matric number and password. Navigate to 'Course Registration' under the Academic menu. "
            "Select your level and semester, check all mandatory core courses and your chosen elective courses "
            "(maximum 24 credit units per semester), and click 'Submit for Departmental Approval'. "
            "Print the generated Course Form in triplicate and present it to your Course Adviser for physical signature."
        ),
    },
    {
        "title": "[DEMO] Undergraduate Admission Requirements",
        "category": "admission",
        "source": "Demo Admissions Brochure",
        "content": (
            "Undergraduate admission requires a minimum of five (5) credit passes in relevant O-Level subjects "
            "(including English Language and Mathematics) obtained in not more than two sittings. Candidates must "
            "also meet the university's institutional UTME cut-off score (200 and above for science disciplines) "
            "and successfully complete the Post-UTME screening exercise."
        ),
    },
    {
        "title": "[DEMO] Semester Examination Guidelines and Regulations",
        "category": "exam_schedule",
        "source": "Demo Examination Committee Regulations",
        "content": (
            "Students must arrive at the examination hall at least 30 minutes before the scheduled start time. "
            "A valid Student Identity Card and a stamped Examination Docket are mandatory for entry. Electronic gadgets, "
            "including mobile phones and programmable smartwatches, are strictly prohibited in the exam hall. "
            "Students who arrive more than 30 minutes after the commencement of the exam will not be admitted."
        ),
    },
    {
        "title": "[DEMO] 2026/2027 Academic Calendar Schedule",
        "category": "academic_calendar",
        "source": "Demo University Senate Calendar",
        "content": (
            "First Semester: Resumption and registration starts October 1. Lectures run for 12 weeks from October 15. "
            "Mid-semester break is December 20 to January 5. Semester examinations commence February 15 and conclude March 5. "
            "Second Semester: Resumption commences April 1; lectures end June 24; examinations run from July 5 to July 25."
        ),
    },
    {
        "title": "[DEMO] Student Portal Troubleshooting and Error Resolution",
        "category": "portal_problem",
        "source": "Demo ICT Support Manual",
        "content": (
            "If you encounter errors on the student portal (e.g. 'Session Expired', 'Access Denied', or 500 internal errors): "
            "1. Clear your browser cache and cookies or try Incognito / Private browsing mode. "
            "2. Ensure you are using an up-to-date modern web browser (Google Chrome, Firefox, or Edge). "
            "3. Verify your network connection. "
            "If courses fail to load after clearing cache or fees payment status is not reflecting, submit a support ticket "
            "under category 'portal_problem' with your matric number and a screenshot of the error."
        ),
    },
    {
        "title": "[DEMO] Student Account Password Recovery Process",
        "category": "password_change",
        "source": "Demo ICT Security Policy",
        "content": (
            "To reset your student portal password: Click 'Forgot Password' on the login page. Enter your registered "
            "institutional email address. A secure password reset link valid for 60 minutes will be sent to your email. "
            "If you no longer have access to your registered email, visit the ICT Helpdesk in the central library building "
            "with your Student ID card or create a support ticket with your department."
        ),
    },
    {
        "title": "[DEMO] Departmental Academic Support and Advising",
        "category": "departmental_issue",
        "source": "Demo Student Affairs Guide",
        "content": (
            "Each academic department maintains designated Course Advisers for each level (100L through 400L/500L). "
            "For issues involving course prerequisites, grade disputes, or academic probation counseling, students "
            "should first consult their Level Adviser during weekly consultation hours. Escalated issues can be brought "
            "to the Head of Department (HOD) office or logged via the backend support ticket system."
        ),
    },
    {
        "title": "[DEMO] Semester Results Verification and CGPA Computation",
        "category": "results",
        "source": "Demo Academic Regulations",
        "content": (
            "Semester results are published on the student portal within four (4) weeks following Senate approval. "
            "The university operates a 5-point CGPA grading system (A=5, B=4, C=3, D=2, E=1, F=0). If an enrolled course "
            "result is missing or marked incomplete (I), file a result query with your departmental exam officer within "
            "two weeks of result publication."
        ),
    },
]

DEMO_FAQS = [
    {
        "question": "How do I register for my semester courses?",
        "answer": "Log in to the student portal, select 'Course Registration', pick your approved core and elective courses (up to 24 units), submit online, and print your Course Form for your Course Adviser's signature.",
        "category": "course_registration",
    },
    {
        "question": "What is the maximum credit units allowed per semester?",
        "answer": "The maximum standard limit is 24 credit units per semester. Any overload requires written approval from the Faculty Dean.",
        "category": "course_registration",
    },
    {
        "question": "What should I do if the student portal displays a 500 error or blank page?",
        "answer": "First, clear your browser cache and cookies or try an incognito window. If the error persists, submit a support ticket with details of the error.",
        "category": "portal_problem",
    },
    {
        "question": "How can I reset my forgotten portal password?",
        "answer": "Click the 'Forgot Password' link on the login page and enter your registered email address to receive a secure password reset token.",
        "category": "password_change",
    },
    {
        "question": "When do first semester examinations begin?",
        "answer": "According to the demo academic calendar, first semester examinations are scheduled to commence in mid-February.",
        "category": "exam_schedule",
    },
    {
        "question": "How is the cumulative grade point average (CGPA) calculated?",
        "answer": "CGPA is computed by dividing total quality points earned (unit × grade value) by the total number of credit units registered across all semesters on a 5.0 scale.",
        "category": "results",
    },
    {
        "question": "What are the requirements for undergraduate admission?",
        "answer": "At least five (5) O-Level credits in relevant subjects including English and Math in not more than two sittings, plus a passing score in the UTME and Post-UTME.",
        "category": "admission",
    },
    {
        "question": "How do I update my personal contact details?",
        "answer": "You can update your phone number and address from your Profile settings in the application or by sending a request to the Academic Records office for official name changes.",
        "category": "personal_details",
    },
    {
        "question": "How do I contact my departmental level adviser?",
        "answer": "Course advisers hold consultation hours during weekdays in their departmental offices. You can also submit an academic support ticket to connect with departmental staff.",
        "category": "departmental_issue",
    },
    {
        "question": "When does the late course registration period end?",
        "answer": "Late registration typically closes two weeks after the formal registration deadline and incurs a late surcharge fee.",
        "category": "course_registration",
    },
]


async def seed_database() -> None:
    print(f"Connecting to MongoDB database '{settings.MONGODB_DATABASE}'...")
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.MONGODB_DATABASE]

    try:
        await client.admin.command("ping")
        print("Connected to MongoDB successfully.")
    except Exception as e:
        print(f"Failed to connect to MongoDB: {e}", file=sys.stderr)
        sys.exit(1)

    print("\n--- Seeding Departments ---")
    dept_map = {}
    for d in DEMO_DEPARTMENTS:
        existing = await db[DEPARTMENTS].find_one({"code": d["code"]})
        if existing:
            dept_map[d["code"]] = existing["_id"]
            print(f"  [EXISTS] Department {d['name']} ({d['code']})")
        else:
            doc = new_department_doc(
                name=d["name"],
                code=d["code"],
                faculty=d["faculty"],
                description=d["description"],
                support_email=d["support_email"],
            )
            res = await db[DEPARTMENTS].insert_one(doc)
            dept_map[d["code"]] = res.inserted_id
            print(f"  [CREATED] Department {d['name']} ({d['code']})")

    print("\n--- Seeding Knowledge Base Documents & Embeddings ---")
    embeddings_provider = get_embeddings_provider()
    for k in DEMO_KNOWLEDGE:
        existing = await db[KNOWLEDGE_BASE].find_one({"title": k["title"]})
        if existing:
            print(f"  [EXISTS] Knowledge doc: {k['title']}")
        else:
            content_to_embed = f"{k['title']}\n\n{k['content']}"
            try:
                embedding = await embeddings_provider.embed_one(content_to_embed)
            except Exception as e:
                print(f"  [WARN] Failed to generate embedding: {e}; using empty vector")
                embedding = []

            doc = new_knowledge_doc(
                title=k["title"],
                content=k["content"],
                category=k["category"],
                created_by=None,
                department_id=dept_map.get("CSC"),
                source=k.get("source"),
                status=KnowledgeStatus.PUBLISHED.value,
                embedding=embedding,
                metadata={"is_demo": True},
            )
            await db[KNOWLEDGE_BASE].insert_one(doc)
            print(f"  [CREATED] Knowledge doc: {k['title']} (embedded {len(embedding)} dims)")

    print("\n--- Seeding FAQs ---")
    for f in DEMO_FAQS:
        existing = await db[FAQS].find_one({"question": f["question"]})
        if existing:
            print(f"  [EXISTS] FAQ: {f['question'][:45]}...")
        else:
            doc = new_faq_doc(
                question=f["question"],
                answer=f["answer"],
                category=f["category"],
                created_by=None,
                status=FAQStatus.PUBLISHED.value,
            )
            await db[FAQS].insert_one(doc)
            print(f"  [CREATED] FAQ: {f['question'][:45]}...")

    client.close()
    print("\nDatabase seeding completed successfully.")


def main() -> None:
    asyncio.run(seed_database())


if __name__ == "__main__":
    main()
