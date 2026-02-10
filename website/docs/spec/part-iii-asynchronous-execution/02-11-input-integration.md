---
title: "11. Input Integration"
sidebar_position: 2
---

### 11.1 Command Pattern Overview

The UGAS input system implements the Command pattern to decouple hardware inputs from ability execution. This separation enables:

- Controller remapping without code changes
- Platform-specific input schemes
- Input buffering and queuing
- Combo system integration

```
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│   Hardware   │─────▶│    Input     │─────▶│    Input     │
│    Input     │      │   Action     │      │     ID       │
└──────────────┘      └──────────────┘      └──────┬───────┘
                                                   │
                                                   ▼
                                            ┌──────────────┐
                                            │   Ability    │
                                            │  Activation  │
                                            └──────────────┘
```

### 11.2 Input Action to Ability Mapping

Abilities are bound to Input IDs, which are mapped from Input Actions:

```yaml
InputMapping:
  Actions:
    - Action: "IA_PrimaryAttack"
      InputID: "Ability.Attack.Primary"
      KeyBindings:
        - Key: "MouseLeft"
        - Key: "GamepadRightTrigger"

    - Action: "IA_SecondaryAttack"
      InputID: "Ability.Attack.Secondary"
      KeyBindings:
        - Key: "MouseRight"
        - Key: "GamepadLeftTrigger"

    - Action: "IA_Ability1"
      InputID: "Ability.Slot.1"
      KeyBindings:
        - Key: "Q"
        - Key: "GamepadFaceLeft"
```

Ability grants include optional Input ID binding:

```typescript
GC.GrantAbility(
  abilityClass: GA_Fireball,
  level: 1,
  inputID: "Ability.Slot.1"
);
```

### 11.3 Input Buffering

Input buffering allows players to queue inputs during animations or recovery frames:

```typescript
struct InputBufferConfig {
  /** Enable input buffering */
  Enabled: boolean;

  /** Buffer window in seconds */
  BufferWindow: float;

  /** Maximum buffered inputs */
  MaxBufferSize: number;
}
```

When input buffering is enabled:

1. Input arrives during "blocked" state (animation, recovery)
2. Input is stored in buffer with timestamp
3. When block ends, buffered inputs are processed in order
4. Expired inputs (beyond buffer window) are discarded

```typescript
function ProcessBufferedInputs(): void {
  const now = GetCurrentTime();

  // Remove expired inputs
  this.InputBuffer = this.InputBuffer.filter(
    input => now - input.Timestamp < this.BufferWindow
  );

  // Process valid inputs
  for (const input of this.InputBuffer) {
    if (TryActivateAbilityByInputID(input.InputID)) {
      break;  // Successfully activated, stop processing
    }
  }

  this.InputBuffer.Clear();
}
```

### 11.4 Remapping Support

Input mappings SHOULD be externalizable and modifiable at runtime:

```typescript
interface IInputMapper {
  /** Get InputID for an action */
  GetInputIDForAction(action: InputAction): InputID;

  /** Remap an action to a new key */
  RemapAction(action: InputAction, newKey: Key): void;

  /** Reset to defaults */
  ResetToDefaults(): void;

  /** Save current mappings */
  SaveMappings(): void;

  /** Load saved mappings */
  LoadMappings(): void;
}
```

---
