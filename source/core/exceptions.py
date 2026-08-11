

class CommittingException(Exception):
    pass

class AuthException(Exception):
    """Базовое исключение для авторизации"""
    pass

class InvalidCredentialsException(AuthException):
    pass

class InvalidTokenException(AuthException):
    pass



class UserException(Exception):
    """Базовое искоючение для пользователей"""
    pass

class UserNotFoundException(UserException):
    pass

class UserInactiveException(UserException):
    pass

class UserNotVerifiedException(UserException):
    pass

class UserAlreadyVerifiedException(UserException):
    pass

class UserAlreadyCreatedVerifyLink(UserException):
    pass

class UserAlreadyCreatedResetpasswordLink(UserException):
    pass

class UsernameAlreadyExsistsException(UserException):
    pass

class EmailAlreadyExsistsException(UserException):
    pass



class PostException(Exception):
    """Базовое искоючение для постов"""
    pass

class PostNotFoundException(PostException):
    pass



class TagException(Exception):
    """Базовое искоючение для тегов"""
    pass

class TagNotFoundException(TagException):
    pass



class CommentException(Exception):
    """Базовое искоючение для комментариев"""
    pass

class CommentNotFoundException(CommentException):
    pass



class FileException(Exception):
    """Базовое искоючение для файлов"""
    pass

class NotAllowedFileTypeException(FileException):
    """Исключение для неподдерживаемых типов файлов"""
    pass

class FileNotFoundException(FileException):
    """Файл не найден в базе"""
    pass

class FileNotInStorageException(FileException):
    """Файл не найден в хранилище"""
    pass

class FileWritingException(FileException):
    """Ошибка при записи файла в хранилище"""
    pass

class FileAddingException(FileException):
    """Ошибка при добавлении файла в базу"""
    pass



class SendEmailException(Exception):
    """Базовое искоючение при отправке письма на почту"""
    pass

class SendEmailHTMLOpeningException(SendEmailException):
    """Ошибка при открытии html файла при формировании сообщения"""
    pass

