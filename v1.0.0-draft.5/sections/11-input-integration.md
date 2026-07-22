## 11. Input Integration

### 11.1 Command Pattern Overview

The UGAS input system implements the Command pattern to decouple hardware inputs from ability execution. This separation enables:

- Controller remapping without code changes

- Platform-specific input schemes

- Input buffering and queuing

- Context-driven input switching via Gameplay Tags

The input layer defines four formal entity schemas that sit between raw hardware and the ability system:

    ┌──────────────┐      ┌──────────────┐      ┌──────────────┐
    │    Device    │─────▶│   Modifier   │─────▶│    Action    │
    │    Input     │      │   Pipeline   │      │   (InputID)  │
    └──────────────┘      └──────────────┘      └──────┬───────┘
                                                       │
                                 ┌──────────────┐      │
                                 │  Action Set  │◀─────┘
                                 │  (context)   │
                                 └──────┬───────┘
                                        │
                                 ┌──────────────┐
                                 │   Ability    │
                                 │  Activation  │
                                 └──────────────┘

The *Mapping* entity connects Device Inputs to Actions, applying Modifiers along the way. Action Sets group Actions into switchable contexts driven by Gameplay Tags on the owning GC.

### 11.2 Input Actions

An Input Action is a named, semantic input intent — the logical "what", not the physical "how". Actions decouple gameplay logic from hardware: an ability binds to the Action `Fire`, never to `Mouse.LeftButton`.

Each Action declares a value type and a trigger behavior:

| Value Type | Description                                                                                     |
|------------|-------------------------------------------------------------------------------------------------|
| Digital    | Boolean on/off. Emits Started/Ongoing/Completed trigger events.                                 |
| Axis1D     | Single float axis (e.g. throttle, steering). Emits a continuous value each frame while nonzero. |
| Axis2D     | Two-component vector (e.g. movement direction, camera look).                                    |
| Axis3D     | Three-component vector (e.g. VR hand position, gyroscope orientation).                          |

| Trigger Behavior | Description                                                    |
|------------------|----------------------------------------------------------------|
| OnPressed        | Fire once when input goes from zero to nonzero (default).      |
| OnReleased       | Fire once when input returns to zero.                          |
| WhileHeld        | Fire every frame while input is nonzero.                       |
| OnTap            | Fire once on press-then-release within `TapThreshold` seconds. |
| OnDoubleTap      | Fire on two taps within `DoubleTapWindow` seconds.             |

``` yaml
Name: Fire
ValueType: Digital
TriggerBehavior: OnPressed
ConsumeInput: true
Tags:
  ActionTags:
    - Input.Type.Combat
Metadata:
  DisplayName: Fire Weapon
  Category: Combat
```

The `Name` field is the value that `InputID` fields on `GrantedAbilities` (§4) and `WaitInputRelease` tasks (§10.3) resolve to. Implementations MUST use exact string matching between `Action.Name` and `InputID`.

`ConsumeInput` controls whether this action consumes the underlying input event. When `true` (the default), lower-priority actions bound to the same hardware input do not receive the event. When `false`, the event propagates.

`Tags.ActionTags` enable bulk operations. A Gameplay Effect that grants the tag `Input.Blocked.Combat` could suppress all actions tagged `Input.Type.Combat` without listing them individually.

### 11.3 Action Sets

An Action Set is a context-based group of Actions that are active together. When a player enters a vehicle, the `OnFoot` set deactivates and the `InVehicle` set activates — driven by the same tag-based activation rules that govern abilities.

``` yaml
Name: OnFoot
Actions:
  - Move
  - Look
  - Fire
  - Aim
  - Reload
  - Jump
  - Sprint
Priority: 0
ActivationTags:
  RequiredTags:
    - State.Alive
  BlockedTags:
    - State.InVehicle
    - State.Cutscene
InputBuffer:
  Enabled: true
  BufferWindow: 0.12
  MaxBufferSize: 2
```

#### Activation Rules

Action Sets activate and deactivate based on the owning GC’s tag state, evaluated whenever owned tags change:

1.  ALL tags in `ActivationTags.RequiredTags` MUST be present on the GC (AND logic).

2.  NONE of the tags in `ActivationTags.BlockedTags` MAY be present (OR logic to block).

3.  Multiple Action Sets MAY be active simultaneously. When two active sets contain the same Action, the set with the highest `Priority` wins for that Action.

4.  When `Exclusive` is `true`, activating this set deactivates all other non-exclusive sets at the same or lower priority. This is appropriate for modal contexts (vehicle controls, cutscenes, menu navigation).

The runtime SHOULD store the list of currently active Action Set names on the GC’s `ActiveActionSets` field for debugging and serialization.

#### Per-Set Input Buffering

Each Action Set MAY override the global input buffer configuration (see §11.7). This enables per-context tuning:

- Fighting games: aggressive buffering (0.1s window, 5 buffer size)

- Platformers: moderate buffering (0.15s window, 3 buffer size)

- Menus: no buffering (avoid accidental double-confirms)

- Driving: no buffering (analog inputs are continuous, not event-based)

### 11.4 Device Inputs

A Device Input is a canonical, engine-agnostic identifier for a physical input on a hardware device. Device Inputs are referenced inline within Mappings using a `Device` + `Input` pair — they are not standalone entity files, since hardware is a finite catalogue, not game-specific authored data.

| Device   | Example Inputs                                                                                                                   |
|----------|----------------------------------------------------------------------------------------------------------------------------------|
| Keyboard | `Key.Space`, `Key.W`, `Key.LeftShift`, `Key.Escape`                                                                              |
| Mouse    | `Mouse.LeftButton`, `Mouse.RightButton`, `Mouse.Axis.X`, `Mouse.Axis.Y`, `Mouse.Scroll`                                          |
| Gamepad  | `Gamepad.FaceBottom` (A/Cross), `Gamepad.FaceRight` (B/Circle), `Gamepad.LeftStick.X`, `Gamepad.RightTrigger`, `Gamepad.DPad.Up` |
| Touch    | `Touch.Tap`, `Touch.Region.Left`, `Touch.Swipe`                                                                                  |
| Gyro     | `Gyro.Pitch`, `Gyro.Yaw`, `Gyro.Roll`                                                                                            |
| Custom   | Extension point for VR controllers, flight sticks, steering wheels. Uses `CustomDeviceName` for disambiguation.                  |

Implementations MUST bridge canonical Device Input identifiers to their engine-specific equivalents at runtime. The canonical naming convention uses hierarchical dot notation: `{Category}.{Identifier}` (e.g. `Key.Space`, `Gamepad.LeftStick.X`).

### 11.5 Input Mappings

A Mapping binds one or more Device Inputs to an Action, within an Action Set and optional platform context. This is the core data file that designers author to define "what button does what."

``` yaml
ActionSet: OnFoot
Platform: PC
Bindings:
  - Action: Fire
    Inputs:
      - Device: Mouse
        Input: Mouse.LeftButton

  - Action: Move
    CompositeInputs:
      Up:
        Device: Keyboard
        Input: Key.W
      Down:
        Device: Keyboard
        Input: Key.S
      Left:
        Device: Keyboard
        Input: Key.A
      Right:
        Device: Keyboard
        Input: Key.D

  - Action: Look
    Inputs:
      - Device: Mouse
        Input: Mouse.Axis.X
      - Device: Mouse
        Input: Mouse.Axis.Y
    Modifiers:
      - MouseSensitivity
```

#### Binding Types

*Simple binding*: A single Device Input maps to an Action. The most common case.

*Chord binding*: Multiple Device Inputs in the `Inputs` array must all be active simultaneously for the binding to fire. Used for modifier keys (Shift+1 for an alternate ability slot). When a chord and a simple binding share an input, the chord SHOULD have a higher `Priority` to avoid the simple binding firing first.

*Composite binding*: The `CompositeInputs` object composes multiple digital inputs into an axis value. The directional slots (`Up`, `Down`, `Left`, `Right`, `Forward`, `Backward`) map to a normalized vector suitable for Axis2D or Axis3D actions. This is how WASD keys produce a 2D movement vector on keyboard.

#### Platform Filtering

When `Platform` is set, the mapping only applies on that platform. Implementations SHOULD resolve platform at load time and discard non-matching mappings. When `Platform` is omitted, the mapping applies universally.

Multiple mapping files MAY target the same Action Set with different platforms, providing platform-specific defaults:

- `input_mapping_onfoot_pc.yaml` — keyboard + mouse bindings

- `input_mapping_onfoot_gamepad.yaml` — gamepad bindings

#### Rebinding

Bindings with `bIsRebindable: true` (the default) SHOULD be modifiable at runtime through the remapping interface (see §11.8). Bindings with `bIsRebindable: false` are fixed and MUST NOT appear in the player’s controls settings screen.

### 11.6 Input Modifiers

An Input Modifier is a reusable processing step applied to raw input values as they flow through the mapping pipeline. Modifiers are standalone entities referenced by name — not inline configuration — enabling sharing across mappings and integration with player settings screens.

| Modifier Type    | Description                                                                                                                                       |
|------------------|---------------------------------------------------------------------------------------------------------------------------------------------------|
| DeadZone         | Clamps values below `InnerThreshold` to zero and above `OuterThreshold` to 1.0. Shape is `Axial` (per-axis) or `Radial` (magnitude of 2D vector). |
| Sensitivity      | Linear multiplier applied to the value. Per-axis multipliers available for 2D actions.                                                            |
| ResponseCurve    | Non-linear response curve. Types: `Linear`, `Exponential` (with `Exponent`), `SCurve`, `Custom` (with explicit `CurvePoints`).                    |
| AxisInvert       | Inverts one or more axes (`InvertX`, `InvertY`).                                                                                                  |
| AxisScale        | Scales axes by arbitrary factors (`ScaleX`, `ScaleY`, `ScaleZ`).                                                                                  |
| AxisSwizzle      | Reorders axes (e.g. `SwizzleOrder: "YXZ"` swaps X and Y).                                                                                         |
| RadialScaling    | Normalizes input to a maximum radius, clamping to the unit circle.                                                                                |
| Normalize        | Normalizes the input vector to unit length.                                                                                                       |
| TriggerThreshold | Converts an analog value to digital: values above `PressThreshold` count as pressed.                                                              |
| Clamp            | Clamps the value between `Min` and `Max`.                                                                                                         |
| Custom           | Engine-specific implementation via `CalculatorClass`.                                                                                             |

``` yaml
Name: StickDeadzone
Type: DeadZone
Params:
  InnerThreshold: 0.15
  OuterThreshold: 0.95
  DeadZoneShape: Radial
UserConfigurable: true
Metadata:
  DisplayName: Stick Dead Zone
```

#### Pipeline Processing

Modifiers in a binding’s `Modifiers` array are processed in order — the output of each modifier feeds into the next. The pipeline runs every frame for axis-type actions and on input events for digital actions.

A typical gamepad stick pipeline:

1.  Raw stick position → `DeadZone` (eliminate drift) → `RadialScaling` (normalize to unit circle) → processed value reaches the Action.

A typical mouse look pipeline:

1.  Raw mouse delta → `Sensitivity` (user-configurable multiplier) → processed value reaches the Action.

#### User-Configurable Modifiers

When `UserConfigurable` is `true`, the runtime SHOULD expose the modifier’s parameters in the player’s settings screen (e.g. a sensitivity slider, an invert-Y toggle, a dead zone adjustment). The modifier’s `Metadata.DisplayName` provides the label for the settings UI.

### 11.7 Input Buffering

Input buffering allows players to queue inputs during animations or recovery frames. The buffer configuration is specified per Action Set (see §11.3) or globally:

``` typescript
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

1.  Input arrives during "blocked" state (animation, recovery)

2.  Input is stored in buffer with timestamp

3.  When block ends, buffered inputs are processed in order

4.  Expired inputs (beyond buffer window) are discarded

``` typescript
function ProcessBufferedInputs(actionSet: ActionSet): void {
  const config = actionSet.InputBuffer ?? this.GlobalBufferConfig;
  if (!config.Enabled) return;

  const now = GetCurrentTime();

  // Remove expired inputs
  this.InputBuffer = this.InputBuffer.filter(
    input => now - input.Timestamp < config.BufferWindow
  );

  // Process valid inputs
  for (const input of this.InputBuffer) {
    if (TryActivateAbilityByInputID(input.ActionName)) {
      break;  // Successfully activated, stop processing
    }
  }

  this.InputBuffer.Clear();
}
```

Buffered inputs MUST only be processed if the Action Set that contains their Action is still active when the buffer is drained.

### 11.8 Remapping Support

Input mappings SHOULD be externalizable and modifiable at runtime:

``` typescript
interface IInputMapper {
  /** Get the active bindings for an action */
  GetBindingsForAction(action: ActionName): Binding[];

  /** Remap a binding to a new device input */
  RemapBinding(action: ActionName, oldInput: DeviceInput, newInput: DeviceInput): void;

  /** Reset all bindings to defaults for an action set */
  ResetToDefaults(actionSet: ActionSetName): void;

  /** Save current mappings to persistent storage */
  SaveMappings(): void;

  /** Load saved mappings from persistent storage */
  LoadMappings(): void;
}
```

Implementations MUST respect the `bIsRebindable` flag on bindings. Only bindings with `bIsRebindable: true` SHOULD be presented in the controls settings UI and accepted by `RemapBinding`.

When a player remaps a binding, the runtime SHOULD check for conflicts (two bindings in the same Action Set using the same Device Input) and either warn the player or swap the conflicting binding.

# Part IV: Feedback, Networking, and Persistence
