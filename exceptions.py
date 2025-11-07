"""Custom exceptions for the reports scraper application.

This module defines a hierarchy of exceptions to provide better error handling
and more informative error messages throughout the application.
"""


class ScraperError(Exception):
    """Base exception for all scraper-related errors.

    This is the base class for all custom exceptions in the application.
    Catching this exception will catch all application-specific errors.
    """

    def __init__(self, message: str, details: str = None):
        """Initialize the exception.

        Args:
            message: Main error message
            details: Additional error details
        """
        self.message = message
        self.details = details
        super().__init__(self.format_message())

    def format_message(self) -> str:
        """Format the complete error message.

        Returns:
            Formatted error message with details if available
        """
        if self.details:
            return f"{self.message}: {self.details}"
        return self.message


class LoginError(ScraperError):
    """Exception raised when login fails.

    This includes invalid credentials, timeout during login,
    or any other login-related failures.
    """

    def __init__(self, username: str, details: str = None):
        """Initialize the login error.

        Args:
            username: Username that failed to login
            details: Additional error details
        """
        message = f"Login failed for user '{username}'"
        super().__init__(message, details)
        self.username = username


class NavigationError(ScraperError):
    """Exception raised when navigation to a page or section fails.

    This includes failures to find menu buttons, links, or timeouts
    during page navigation.
    """

    def __init__(self, target: str, details: str = None):
        """Initialize the navigation error.

        Args:
            target: Target page or section that failed to navigate to
            details: Additional error details
        """
        message = f"Failed to navigate to '{target}'"
        super().__init__(message, details)
        self.target = target


class ProductAccessError(ScraperError):
    """Exception raised when a product is not available for the user.

    This occurs when trying to access a product filter that the user
    doesn't have permission to use.
    """

    def __init__(self, product: str, username: str, details: str = None):
        """Initialize the product access error.

        Args:
            product: Product name that is not available
            username: Username attempting to access the product
            details: Additional error details
        """
        message = (
            f"Product '{product}' not available for user '{username}'"
        )
        super().__init__(message, details)
        self.product = product
        self.username = username


class DownloadError(ScraperError):
    """Exception raised when a report download fails.

    This includes timeouts, network errors, or failures to convert
    the downloaded file.
    """

    def __init__(self, report_type: str, details: str = None):
        """Initialize the download error.

        Args:
            report_type: Type of report that failed to download
            details: Additional error details
        """
        message = f"Failed to download {report_type} report"
        super().__init__(message, details)
        self.report_type = report_type


class TabSwitchError(ScraperError):
    """Exception raised when switching to a report tab fails.

    This occurs when the desired tab cannot be found or clicked.
    """

    def __init__(self, tab_name: str, available_tabs: list = None):
        """Initialize the tab switch error.

        Args:
            tab_name: Name of the tab that couldn't be switched to
            available_tabs: List of available tab names
        """
        details = None
        if available_tabs:
            details = f"Available tabs: {', '.join(available_tabs)}"

        message = f"Failed to switch to tab '{tab_name}'"
        super().__init__(message, details)
        self.tab_name = tab_name
        self.available_tabs = available_tabs


class ConfigurationError(ScraperError):
    """Exception raised when configuration is invalid or missing.

    This includes missing config files, invalid values, or
    malformed configuration data.
    """

    def __init__(self, config_name: str, details: str = None):
        """Initialize the configuration error.

        Args:
            config_name: Name of the configuration that is invalid
            details: Additional error details
        """
        message = f"Invalid or missing configuration: {config_name}"
        super().__init__(message, details)
        self.config_name = config_name


class ValidationError(ScraperError):
    """Exception raised when data validation fails.

    This includes invalid user credentials, malformed filenames,
    or invalid date ranges.
    """

    def __init__(self, field_name: str, value: any, details: str = None):
        """Initialize the validation error.

        Args:
            field_name: Name of the field that failed validation
            value: Invalid value
            details: Additional validation error details
        """
        message = f"Validation failed for {field_name}: {value}"
        super().__init__(message, details)
        self.field_name = field_name
        self.value = value


class FileOperationError(ScraperError):
    """Exception raised when file operations fail.

    This includes failures to read, write, or convert files.
    """

    def __init__(
        self,
        operation: str,
        filename: str,
        details: str = None
    ):
        """Initialize the file operation error.

        Args:
            operation: Operation that failed (read, write, convert, etc.)
            filename: File involved in the operation
            details: Additional error details
        """
        message = f"Failed to {operation} file '{filename}'"
        super().__init__(message, details)
        self.operation = operation
        self.filename = filename


class ReportProcessingError(ScraperError):
    """Exception raised when report processing fails.

    This includes failures during report combination, data extraction,
    or Excel manipulation.
    """

    def __init__(self, report_type: str, details: str = None):
        """Initialize the report processing error.

        Args:
            report_type: Type of report being processed
            details: Additional error details
        """
        message = f"Failed to process {report_type} report"
        super().__init__(message, details)
        self.report_type = report_type


class BrowserError(ScraperError):
    """Exception raised when browser operations fail.

    This includes failures to launch the browser, create contexts,
    or locate Playwright binaries.
    """

    def __init__(self, details: str = None):
        """Initialize the browser error.

        Args:
            details: Browser error details
        """
        message = "Browser operation failed"
        super().__init__(message, details)


# Maintain backward compatibility with ProductNotAvailableError
# This was used in the original code
ProductNotAvailableError = ProductAccessError
