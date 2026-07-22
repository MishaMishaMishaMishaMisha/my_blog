from fastapi import APIRouter
from fastapi import Depends
from source.database.db_connect import get_db
from source.dependencies.user import get_user_service
from source.core.exceptions import (UsernameAlreadyExsistsException, 
                                    InvalidCredentialsException,
                                    UserNotFoundException, 
                                    EmailAlreadyExsistsException,
                                    InvalidTokenException,
                                    UserInactiveException,
                                    UserAlreadyVerifiedException)
from fastapi import HTTPException
from source.dependencies.auth import get_auth_service
from source.core.logger import default_logger
from source.schemas.user import UserEmailDTO, UserResetPasswordDTO
from source.services.auth import AuthService
from fastapi import Response, Request
from fastapi.security import OAuth2PasswordRequestForm
from source.models.user import UserModel
from source.dependencies.auth import get_user_from_token
from source.services.email import EmailService
from source.dependencies.verify_user import get_verify_user_service
from typing import Annotated
from fastapi import Query
from source.tasks.email_task import send_message_to_email
from source.services.verify_user import VerifyUserService


router = APIRouter(prefix="/auth", tags=["Auth"])


# отдадим access токен в теле ответа, а refresh токен в куках
@router.post("/login")
async def login_user(#form_data: UserLoginDTO,
                     response: Response,
                     form_data: OAuth2PasswordRequestForm = Depends(), # данные должны прийти не json, а data
                     auth_service: AuthService = Depends(get_auth_service)) -> dict:
    
    try:
        default_logger.info(f"Authenication user: TRYING, login={form_data.username}")
        tokens = await auth_service.authenticate_user(login=form_data.username,
                                                      password=form_data.password)
        
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
        raise HTTPException(status_code=401, detail=str(e))

@router.post("/logout")
async def logout_user(response: Response) -> dict:
    response.delete_cookie(key="refresh_token")
    return {"message": "Logged out successfully"}


# update access token
@router.post("/refresh")
async def update_token(request: Request,
                       response: Response,
                       auth_service: AuthService = Depends(get_auth_service)) -> dict:
    
    default_logger.info(f"Updating tokens: trying")
    
    # достаем refresh токен
    refresh_token = request.cookies.get("refresh_token")
    
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token missing")
        
    try:
        # Метод генерирует новую пару токенов
        new_tokens = await auth_service.update_refresh_token(refresh_token)
        
        # Перезаписываем новую куку
        response.set_cookie(
            key="refresh_token",
            value=new_tokens.refresh_token,
            httponly=True,
            secure=True,
            samesite="lax"
        )
        
        return {"access_token": new_tokens.access_token, "token_type": "bearer"}
    
    except InvalidTokenException as e:
        raise HTTPException(status_code=401, detail=str(e))



@router.post("/resend-verification-email")
async def resend_verify_email(user: UserModel = Depends(get_user_from_token),
                              verify_user_service: VerifyUserService = Depends(get_verify_user_service)
                              ) -> dict:
    
    default_logger.info("Resend verification email")
    
    if user.is_verified:
        return {"message": "your account already verified"}
    
    # # add celery later
    # link = email_service.create_verify_link(user.id)
    # msg = email_service.prepareEmailMsg(email_receiver=user.email,
    #                                     message_subject="Link for verification account",
    #                                     message_body=link)
    # email_service.sendEmail(msg)
    
    # add task to celery
    link = verify_user_service.create_verify_link(user.id)
    send_message_to_email.delay(user_email=user.email, 
                                        msg_subject="Link for verification account", 
                                        msg_body=link)
    
    return {"message": "verification link sent to email"}

@router.get("/verify-email")
async def verify_user(token: Annotated[str, Query(title="verification token")],
                      verify_user_service: VerifyUserService = Depends(get_verify_user_service)
                      ) -> dict:
    
    try:
        
        default_logger.info("Verification user: TRYING")
        await verify_user_service.verify_email(token)
        default_logger.info("Verification user: user verified")
        
        return {"message": "user verified successfully"}
    
    except InvalidTokenException as e:
        raise HTTPException(status_code=401, detail=str(e))
        
    except UserNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    except UserInactiveException as e:
        raise HTTPException(status_code=401, detail=str(e))
    
    except UserAlreadyVerifiedException as e:
        raise HTTPException(status_code=401, detail=str(e))
    
    

#POST /auth/forgot-password
@router.post("/forgot-password")
async def forgot_password(email_data: UserEmailDTO,
                          verify_user_service: VerifyUserService = Depends(get_verify_user_service)
                          ) -> dict:
    
    default_logger.info("User forgot password")
    
    user = await verify_user_service.find_user_by_email(email_data.email)
    if not user:
        raise HTTPException(status_code=404, detail="email not found")
    
    # # add celery later
    # link = email_service.create_resetPassword_link(user.id)
    # msg = email_service.prepareEmailMsg(email_receiver=user.email,
    #                                     message_subject="Link for resetting password",
    #                                     message_body=link)
    # email_service.sendEmail(msg)
    
    # add task to celery
    default_logger.info("User forgot password: sending resetting password link to email")
    link = verify_user_service.create_resetPassword_link(user.id)
    send_message_to_email.delay(user_email=user.email, 
                                        msg_subject="Link for resetting password", 
                                        msg_body=link)
    
    return {"message": "resetting password link send to email"}


#POST /auth/reset-password
@router.post("/reset-password")
async def reset_password(password_data: UserResetPasswordDTO,
                         verify_user_service: VerifyUserService = Depends(get_verify_user_service)
                         ) -> dict:
    
    try:
        default_logger.info("User resetting password: TRYING")
        await verify_user_service.reset_password(password_data.token, password_data.new_password)
        default_logger.info("ser resetting password: password changed")
        
        return {"message": "user changed password successfully"}
    
    except InvalidTokenException as e:
        raise HTTPException(status_code=401, detail=str(e))
        
    except UserNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    except UserInactiveException as e:
        raise HTTPException(status_code=401, detail=str(e))
    
    
    