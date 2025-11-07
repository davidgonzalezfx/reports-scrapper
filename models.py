"""Data models and dataclasses for the reports scraper application.

This module contains all data transfer objects (DTOs) and models used
throughout the application for type safety and clear data structures.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime


@dataclass
class UserCredentials:
    """User login credentials."""

    username: str
    password: str

    def validate(self) -> bool:
        """Validate that credentials are not empty.

        Returns:
            True if both username and password are present
        """
        return bool(self.username and self.password)


@dataclass
class UserResult:
    """Result of processing a single user during scraping.

    Attributes:
        username: Username that was processed
        success: Whether processing succeeded
        error: Error message if processing failed
        error_type: Category of error (login, product_access, navigation, etc.)
        reports_downloaded: Number of reports successfully downloaded
        reports_attempted: Total number of reports attempted
    """

    username: str
    success: bool
    error: Optional[str] = None
    error_type: Optional[str] = None
    reports_downloaded: int = 0
    reports_attempted: int = 0


@dataclass
class ScraperResult:
    """Overall result of the scraper execution.

    Attributes:
        success: Whether at least one user was processed successfully
        users_processed: Number of users successfully processed
        total_users: Total number of users attempted
        user_results: List of individual user results
        warnings: List of warning messages
    """

    success: bool
    users_processed: int
    total_users: int
    user_results: List[UserResult] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def get_error_summary(self) -> str:
        """Get a summary of all errors that occurred.

        Returns:
            Human-readable error summary string
        """
        if not self.user_results:
            return "No users were processed"

        errors = [r for r in self.user_results if not r.success]
        if not errors:
            return f"All {self.users_processed} users processed successfully"

        # Group errors by type
        error_groups: Dict[str, List[UserResult]] = {}
        for result in errors:
            error_type = result.error_type or 'unknown'
            if error_type not in error_groups:
                error_groups[error_type] = []
            error_groups[error_type].append(result)

        # Build summary
        summaries = []
        for error_type, results in error_groups.items():
            if error_type == 'product_access':
                for result in results:
                    summaries.append(
                        f"User '{result.username}': {result.error}"
                    )
            elif error_type == 'login':
                usernames = [r.username for r in results]
                summaries.append(f"Login failed for: {', '.join(usernames)}")
            else:
                usernames = [r.username for r in results]
                summaries.append(
                    f"{error_type.replace('_', ' ').title()} error for: "
                    f"{', '.join(usernames)}"
                )

        return " | ".join(summaries) if summaries else (
            "Errors occurred during processing"
        )


@dataclass
class FileInfo:
    """Information about a report file.

    Attributes:
        filename: Full filename
        user: Username associated with the file
        report_name: Name of the report type
    """

    filename: str
    user: str
    report_name: str


@dataclass
class CombinedReportInfo:
    """Information about a combined reports file.

    Attributes:
        filename: Full filename
        size: File size in bytes
        modified: Last modification datetime
    """

    filename: str
    size: int
    modified: datetime


@dataclass
class SchoolSummary:
    """Summary statistics for the entire school.

    Attributes:
        all_teachers: Total number of teachers
        all_students: Total number of students
        total_listen: Total listen activities
        total_read: Total read activities
        total_quizzes: Total quiz activities
        total_activities: Sum of all activities
    """

    all_teachers: int
    all_students: int
    total_listen: int
    total_read: int
    total_quizzes: int
    total_activities: int


@dataclass
class ClassroomSummary:
    """Summary statistics for a single classroom.

    Attributes:
        name: Classroom name
        students: Total number of students
        students_used: Number of students who used the tool
        usage: Usage percentage (0-100)
        listen: Total listen activities
        read: Total read activities
        quiz: Total quiz activities
        interactivity: Total interactivity score
        practice_recording: Total practice recording activities
    """

    name: str
    students: int
    students_used: int
    usage: float
    listen: int
    read: int
    quiz: int
    interactivity: int
    practice_recording: int


@dataclass
class SkillData:
    """Reading skill proficiency data for a student.

    Attributes:
        name: Skill name
        correct: Number of correct answers
        total: Total number of questions
        accuracy: Accuracy percentage (0-100)
    """

    name: str
    correct: int
    total: int
    accuracy: float


@dataclass
class ClassroomSkills:
    """Reading skills data for a classroom.

    Attributes:
        classroom: Classroom name
        skills: List of skill proficiency data
    """

    classroom: str
    skills: List[SkillData] = field(default_factory=list)


@dataclass
class TopReader:
    """Top reader student information.

    Attributes:
        name: Student name
        score: Combined listen + read score
    """

    name: str
    score: float


@dataclass
class ClassroomTopReaders:
    """Top readers for a classroom.

    Attributes:
        name: Classroom name
        students: List of top reader students
    """

    name: str
    students: List[TopReader] = field(default_factory=list)


@dataclass
class LevelUpStudent:
    """Level up progress for a student.

    Attributes:
        student: Student name
        level: Current reading level
        progress: Progress percentage (0-100)
    """

    student: str
    level: str
    progress: float


@dataclass
class ClassroomLevelUp:
    """Level up progress data for a classroom.

    Attributes:
        classroom: Classroom name
        students: List of student level up progress
    """

    classroom: str
    students: List[LevelUpStudent] = field(default_factory=list)


@dataclass
class ClassroomComparison:
    """Comparison data for classroom charts.

    Attributes:
        labels: List of classroom names
        listen: List of listen activity counts
        read: List of read activity counts
        quiz: List of quiz activity counts
    """

    labels: List[str]
    listen: List[int]
    read: List[int]
    quiz: List[int]


@dataclass
class NotificationMessage:
    """Application notification message.

    Attributes:
        message: Notification text
        type: Notification type (info, warning, error, success)
        timestamp: When the notification was created
    """

    message: str
    type: str
    timestamp: str

    @classmethod
    def create(cls, message: str, type: str = 'info') -> "NotificationMessage":
        """Create a notification with current timestamp.

        Args:
            message: Notification text
            type: Notification type

        Returns:
            NotificationMessage instance
        """
        return cls(
            message=message,
            type=type,
            timestamp=datetime.now().isoformat()
        )
