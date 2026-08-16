from fastapi import (APIRouter,
                     Depends,
                     HTTPException,
                     status,
                     Response, 
                     Request, 
                     Query)
from fastapi.security import OAuth2PasswordRequestForm
from typing import Annotated

from source.models.user import UserModel
from source.tasks.email_task import send_html_message_to_email
from source.schemas.user import UserEmailDTO, UserResetPasswordDTO

from source.core.logger import default_logger
from source.core.exceptions import (InvalidCredentialsException,
                                    UserNotFoundException, 
                                    InvalidTokenException,
                                    UserInactiveException,
                                    UserAlreadyVerifiedException,
                                    UserAlreadyCreatedVerifyLink,
                                    UserAlreadyCreatedResetpasswordLink)

from source.services.auth import AuthService
from source.services.verify_user import VerifyUserService

from source.dependencies.auth import get_auth_service
from source.dependencies.auth import get_user_from_token
from source.dependencies.verify_user import get_verify_user_service
from source.dependencies.rate_limit import (login_limiter,
                                            logout_limiter,
                                            refresh_token_limiter,
                                            resend_verify_email_limiter,
                                            verify_email_limiter,
                                            forgot_password_email_limiter,
                                            reset_password_limiter)


router = APIRouter(prefix="/auth", tags=["Auth"])


# отдадим access токен в теле ответа, а refresh токен в куках
@router.post("/login", 
             dependencies=[Depends(login_limiter)])
async def login_user(response: Response,
                     # данные должны прийти не json, а data
                     form_data: OAuth2PasswordRequestForm = Depends(),
                     auth_service: AuthService = Depends(get_auth_service)) -> dict:
    
    try:
        default_logger.info(f"Authenication user: TRYING, login={form_data.username}")
        tokens = await auth_service.authenticate_user(login=form_data.username,
                                                      password=form_data.password)
        
        default_logger.info("Authenication user: done}")
        
        # добавляем refresh_token в куку с защитой
        response.set_cookie(
            key="refresh_token",
            value=tokens.refresh_token,
            httponly=True,  # Защита от XSS (JS не сможет прочитать куку)
            secure=True,    # Только по HTTPS (в режиме разработки FastAPI это прощает)
            samesite="lax"  # Защита от CSRF
        )
        # А access_token отдаем в теле ответа
        return {"access_token": tokens.access_token, "token_type": "bearer"}
        
    except InvalidCredentialsException as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, 
                            detail=str(e))


@router.post("/logout", 
             dependencies=[Depends(logout_limiter)])
async def logout_user(request: Request,
                      response: Response) -> dict:
    
    default_logger.info("Logout user")
    
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        return {"message": "Refresh token already deleted"}
    
    response.delete_cookie(key="refresh_token")
    return {"message": "Logged out successfully"}


# update access token
@router.post("/refresh", 
             dependencies=[Depends(refresh_token_limiter)])
async def update_token(request: Request,
                       response: Response,
                       auth_service: AuthService = Depends(get_auth_service)) -> dict:
    
    default_logger.info("Updating tokens: trying")
    
    # достаем refresh токен
    refresh_token = request.cookies.get("refresh_token")
    
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, 
                            detail="Refresh token missing")
        
    try:
        # генерируем новую пару токенов
        new_tokens = await auth_service.update_refresh_token(refresh_token)
        
        # Перезаписываем новую куку
        response.set_cookie(
            key="refresh_token",
            value=new_tokens.refresh_token,
            httponly=True,
            secure=True,
            samesite="lax"
        )
        
        default_logger.info("Updating tokens: done")
        
        return {"access_token": new_tokens.access_token, "token_type": "bearer"}
    
    except InvalidTokenException as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, 
                            detail=str(e))


@router.post("/resend-verification-email", 
             dependencies=[Depends(resend_verify_email_limiter)])
async def resend_verify_email(user: UserModel = Depends(get_user_from_token),
                              verify_user_service: VerifyUserService = Depends(get_verify_user_service)
                              ) -> dict:
    
    default_logger.info(f"Resend verification email to user <{user.username}>: trying")
    
    if user.is_verified:
        return {"message": "your account already verified"}
    
    try:
        link = await verify_user_service.create_verify_link(user.id)
        msg_data = verify_user_service.create_verify_email_msg_data(link, user.username)

        send_html_message_to_email.delay(user_email=user.email, 
                                         msg_subject=msg_data.get("subject"),
                                         html_path=msg_data.get("template_path"),
                                         context=msg_data.get("context"),
                                         text_content=msg_data.get("text_version"))
        
        default_logger.info("Resend verification email: done")
        
        return {"message": "verification link sent to email"}
    
    except UserAlreadyCreatedVerifyLink as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, 
                            detail=str(e))


@router.get("/verify-email", 
            dependencies=[Depends(verify_email_limiter)])
async def verify_user(token: Annotated[str, Query(title="verification token")],
                      verify_user_service: VerifyUserService = Depends(get_verify_user_service)
                      ) -> dict:
    
    try:
        default_logger.info("Verification user: TRYING")
        await verify_user_service.verify_email(token)
        default_logger.info("Verification user: user verified")
        
        return {"message": "user verified successfully"}
    
    except InvalidTokenException as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, 
                            detail=str(e))
        
    except UserNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, 
                            detail=str(e))
    
    except UserInactiveException as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, 
                            detail=str(e))
    
    except (UserAlreadyVerifiedException, UserAlreadyCreatedVerifyLink) as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, 
                            detail=str(e))
    
    
@router.post("/forgot-password", 
             dependencies=[Depends(forgot_password_email_limiter)])
async def forgot_password(email_data: UserEmailDTO,
                          verify_user_service: VerifyUserService = Depends(get_verify_user_service)
                          ) -> dict:
    
    default_logger.info("User forgot password: check email")
    
    user = await verify_user_service.find_user_by_email(email_data.user_email)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, 
                            detail="email not found")
    
    try:
        default_logger.info("User forgot password: sending msg to email")
        link = await verify_user_service.create_resetPassword_link(user.id)
        msg_data = verify_user_service.create_reset_password_msg_data(link, user.username)
        
    except UserAlreadyCreatedResetpasswordLink as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, 
                            detail=str(e))
    
    else:
        # add task to celery
        
        default_logger.info("!!before ceclery!!")
        default_logger.info(f"data type= {type(msg_data)}")
        default_logger.info(f"data= {msg_data}")
        # default_logger.info("html pathp=", msg_data.get("template_path"))
        # default_logger.info("context=", msg_data.get("context"))
        # default_logger.info("text vers=", msg_data.get("text_version"))
        default_logger.info("!!before ceclery!!")
        
        send_html_message_to_email.delay(user_email=user.email, 
                                         msg_subject=msg_data.get("subject"),
                                         html_path=msg_data.get("template_path"),
                                         context=msg_data.get("context"),
                                         text_content=msg_data.get("text_version"))
    
    default_logger.info("User forgot password: done")
    return {"message": "resetting password link send to email"}


@router.post("/reset-password", 
             dependencies=[Depends(reset_password_limiter)])
async def reset_password(password_data: UserResetPasswordDTO,
                         verify_user_service: VerifyUserService = Depends(get_verify_user_service)
                         ) -> dict:
    
    try:
        default_logger.info("User resetting password: TRYING")
        await verify_user_service.reset_password(password_data.token, password_data.new_password)
        default_logger.info("User resetting password: password changed")
        
        return {"message": "User changed password successfully"}
    
    except InvalidTokenException as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, 
                            detail=str(e))
        
    except UserNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, 
                            detail=str(e))
    
    except UserInactiveException as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, 
                            detail=str(e))
    
    
    