# Anima LoRA 단계 스케줄러

[English](README.md) | Korean

Anima LoRA 단계 스케줄러는 Anima LoRA가 샘플링 과정에서 영향을 주는 시점을 제어하는 Forge/WebUI 확장입니다. LoRA를 구도, 캐릭터 특징, 스타일 단계에만 적용할 수 있고 기본 패스와 Hires. fix 패스에 서로 다른 스케줄을 줄 수 있습니다.

## 기능

- 모델 파일을 수정하지 않고 Anima 모델용 LoRA 단계 스케줄링을 적용합니다.
- 구도, 캐릭터 특징, 스타일 단계용 기본 템플릿을 제공합니다.
- 적용과 차단 모드를 지원하여 특정 단계에서만 LoRA를 켜거나 0으로 만들 수 있습니다.
- Shift 값에 맞춰 타이밍 창을 자동으로 조정합니다.
- 기본 패스와 Hires. fix 패널을 분리할 수 있습니다.
- Hires. fix에서 전체 LoRA 또는 지정한 전체 LoRA 태그를 비활성화할 수 있습니다.
- LoRA별 템플릿 덮어쓰기를 지원합니다.
- 템플릿 저장, 이름 변경, 삭제, 기본 프리셋 조합 생성을 지원합니다.
- Settings에서 `en`과 `ko` 언어를 선택할 수 있습니다.

## 설치

1. 이 폴더를 `stable-diffusion-webui/extensions` 또는 `sd-webui-forge-neo/extensions`에 복사합니다.
2. WebUI를 재시작하거나 Reload UI를 실행합니다.
3. txt2img 또는 img2img에서 **Anima LoRA 단계 스케줄러**를 엽니다.

## 기본 사용법

1. **단계 스케줄링 사용**을 켭니다.
2. 대상 범위를 선택합니다.
   - Anima LoRA 자동 감지: Anima로 감지된 LoRA에만 적용합니다.
   - 프롬프트의 모든 LoRA: 프롬프트 안의 모든 LoRA 태그에 적용합니다.
   - 대상 목록만: 대상 필드에 입력한 이름에만 적용합니다.
   - 대상 목록 제외: 대상 필드에 입력한 이름만 빼고 프롬프트 LoRA에 적용합니다.
3. `style-stage`, `composition-stage`, `character-feature-stage` 같은 템플릿을 선택합니다.
4. 일반적인 Anima/DiT 작업에서는 **Shift 기준 자동 타이밍**을 켜 둡니다.
5. 평소처럼 생성하면 확장이 샘플링 중 LoRA patch 강도를 조절합니다.

## 타이밍 설정

- **시작 비율**과 **종료 비율**은 `0`부터 `1`까지의 샘플링 진행 값입니다.
- **피크 비율**은 단계 곡선이 가장 강한 지점입니다.
- **단계 강도 배율**은 활성 창 안에서 최종 LoRA 강도에 곱해집니다.
- **강도 곡선**은 smooth, hold, triangle, front-heavy, back-heavy 방식으로 변화를 제어합니다.
- **Shift**는 Forge Shift / Distilled CFG 컨트롤에서 읽습니다. 자동 템플릿은 현재 Shift에 맞춰 타이밍을 조정합니다.

## LoRA별 템플릿

한 줄에 하나의 규칙을 입력합니다.

```text
lora_name=template_name
<lora:name:0.8>=template_name
```

규칙이 없는 LoRA는 패널에서 선택한 템플릿을 사용합니다.

## 템플릿 관리

템플릿 관리에서 현재 기본 패널을 템플릿으로 저장하고, 사용자 템플릿의 이름 변경과 삭제를 할 수 있습니다. 기본 단계 프리셋을 조합해 새 템플릿을 만들 수도 있습니다. 내장 템플릿은 덮어쓰기, 이름 변경, 삭제가 불가능합니다.

## 언어 설정

**Settings**에서 **Anima LoRA Stage Scheduler**를 찾고 언어를 `en` 또는 `ko`로 선택한 뒤 Reload UI를 실행합니다.

## 참고

- 기존 템플릿 값은 호환성을 위해 canonical English ID로 자동 마이그레이션됩니다.
- 확장은 샘플링 중 LoRA patch 강도만 제어하며 checkpoint나 LoRA 파일을 수정하지 않습니다.
- 먼저 중간 정도 LoRA 가중치로 테스트하고, 강한 단계 스케줄을 너무 많이 겹치지 않는 것을 권장합니다.
