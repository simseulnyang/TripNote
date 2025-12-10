import google.generativeai as genai
from django.conf import settings
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiResponse

from .models import ChatSession, ChatMessage
from .serializers import (
    ChatSessionSerializer,
    ChatSessionListSerializer,
    ChatRequestSerializer,
    ChatMessageSerializer,
)

# Gemini 설정
genai.configure(api_key=settings.GEMINI_API_KEY)

SYSTEM_PROMPT = """당신은 친절하고 전문적인 여행 플래너 AI입니다.

역할:
- 사용자의 여행 계획을 도와주세요
- 여행지, 맛집, 관광명소, 숙소 등을 추천해주세요
- 예산, 일정, 동행자 유형에 맞는 맞춤 추천을 해주세요

응답 형식:
- 여행 일정을 요청받으면 아래 형식으로 응답하세요:

📅 [여행지] [N박 M일] 여행 일정

🗓️ DAY 1 - [테마]
- [시간대] [장소명]
  - 설명 및 추천 이유
  - 💰 예상 비용

🗓️ DAY 2 - [테마]
...

💡 여행 TIP
- 유용한 팁들

💰 예상 총 경비: 약 OO만원

응답 스타일:
- 친근하고 따뜻한 톤
- 이모지 적절히 사용
- 구체적이고 실용적인 정보 제공

제한:
- 여행과 관련없는 질문은 정중히 여행 관련 대화로 유도
"""


class ChatSessionListView(APIView):
    """채팅 세션 목록 조회 / 생성"""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['AI Chat_list_GET'],
        summary='채팅 세션 목록 조회',
        description='현재 로그인한 사용자의 모든 채팅 세션 목록을 조회합니다.',
        responses={
            200: ChatSessionListSerializer(many=True),
            401: OpenApiResponse(description='인증 실패'),
        }
    )
    def get(self, request):
        sessions = ChatSession.objects.filter(user=request.user)
        serializer = ChatSessionListSerializer(sessions, many=True)
        return Response(serializer.data)

    @extend_schema(
        tags=['AI Chat_list_POST'],
        summary='새 채팅 세션 생성',
        description='새로운 채팅 세션을 생성합니다.',
        request={'application/json': {'type': 'object', 'properties': {'title': {'type': 'string', 'example': '제주도 여행'}}}},
        responses={
            201: ChatSessionSerializer,
            401: OpenApiResponse(description='인증 실패'),
        }
    )
    def post(self, request):
        session = ChatSession.objects.create(
            user=request.user,
            title=request.data.get('title', '새 대화')
        )
        serializer = ChatSessionSerializer(session)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ChatSessionDetailView(APIView):
    """채팅 세션 상세 조회 / 삭제"""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['AI Chat_detail_GET'],
        summary='채팅 세션 상세 조회',
        description='특정 채팅 세션의 상세 정보와 메시지 목록을 조회합니다.',
        responses={
            200: ChatSessionSerializer,
            401: OpenApiResponse(description='인증 실패'),
            404: OpenApiResponse(description='세션을 찾을 수 없음'),
        }
    )
    def get(self, request, session_id):
        try:
            session = ChatSession.objects.get(id=session_id, user=request.user)
        except ChatSession.DoesNotExist:
            return Response({'error': '세션을 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = ChatSessionSerializer(session)
        return Response(serializer.data)

    @extend_schema(
        tags=['AI Chat_detail_DELETE'],
        summary='채팅 세션 삭제',
        description='특정 채팅 세션과 관련된 모든 메시지를 삭제합니다.',
        responses={
            204: OpenApiResponse(description='삭제 성공'),
            401: OpenApiResponse(description='인증 실패'),
            404: OpenApiResponse(description='세션을 찾을 수 없음'),
        }
    )
    def delete(self, request, session_id):
        try:
            session = ChatSession.objects.get(id=session_id, user=request.user)
        except ChatSession.DoesNotExist:
            return Response({'error': '세션을 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)
        
        session.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ChatMessageView(APIView):
    """AI 채팅 메시지 전송"""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['AI Chat_send_POST'],
        summary='AI에게 메시지 전송',
        description='AI 여행 플래너에게 메시지를 보내고 응답을 받습니다. session_id가 없으면 새 세션이 자동 생성됩니다.',
        request=ChatRequestSerializer,
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'session_id': {'type': 'integer', 'example': 1},
                    'message': {
                        'type': 'object',
                        'properties': {
                            'id': {'type': 'integer', 'example': 1},
                            'role': {'type': 'string', 'example': 'assistant'},
                            'content': {'type': 'string', 'example': '📅 강릉 2박 3일 여행 일정...'},
                            'created_at': {'type': 'string', 'example': '2025-12-10T10:00:00Z'},
                        }
                    }
                }
            },
            401: OpenApiResponse(description='인증 실패'),
            404: OpenApiResponse(description='세션을 찾을 수 없음'),
        }
    )
    def post(self, request):
        serializer = ChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_message = serializer.validated_data['message']
        session_id = serializer.validated_data.get('session_id')

        # 세션 가져오기 또는 생성
        if session_id:
            try:
                session = ChatSession.objects.get(id=session_id, user=request.user)
            except ChatSession.DoesNotExist:
                return Response({'error': '세션을 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)
        else:
            title = user_message[:30] + '...' if len(user_message) > 30 else user_message
            session = ChatSession.objects.create(user=request.user, title=title)

        # 사용자 메시지 저장
        ChatMessage.objects.create(session=session, role='user', content=user_message)

        # 이전 대화 내역 (최근 20개)
        previous_messages = list(session.messages.order_by('created_at'))
        
        # Gemini용 대화 히스토리 구성 (현재 메시지 제외)
        history = []
        for msg in previous_messages[:-1]:
            history.append({
                'role': 'user' if msg.role == 'user' else 'model',
                'parts': [msg.content]
            })

        # Gemini API 호출
        try:
            model = genai.GenerativeModel(
                model_name='gemini-2.0-flash',
                system_instruction=SYSTEM_PROMPT
            )
            
            chat = model.start_chat(history=history)
            response = chat.send_message(user_message)
            ai_response = response.text

        except Exception as e:
            ai_response = "죄송합니다. 일시적인 오류가 발생했습니다. 잠시 후 다시 시도해주세요."
            print(f"Gemini API Error: {e}")

        # AI 응답 저장
        ai_message = ChatMessage.objects.create(
            session=session,
            role='assistant',
            content=ai_response
        )

        return Response({
            'session_id': session.id,
            'message': ChatMessageSerializer(ai_message).data,
        })