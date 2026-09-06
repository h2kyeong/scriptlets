// in order to use usbMIDI need to visit Tools > USB Type
// and set to MIDI
#include <MIDI.h>

void process(uint8_t);

const uint8_t VELOCITY = 100;
const uint8_t MIDI_CHANNEL = 10;
const uint8_t START_NOTE = 36; // C2 (Adjust base MIDI note as needed)
const unsigned long DEBOUNCE_DELAY = 60; // Debounce time in milliseconds

// State arrays indexed by pin number
bool lastPinState[NUM_DIGITAL_PINS];
unsigned long lastDebounceTime[NUM_DIGITAL_PINS];

void setup() {
  for (uint8_t i=0; i < CORE_NUM_TOTAL_PINS; ++i)
    pinMode(i, INPUT_PULLUP);
  for (uint8_t pin = 0; pin < NUM_DIGITAL_PINS; pin++) {
    lastPinState[pin] = digitalRead(pin);
    lastDebounceTime[pin] = 0;
  }
}

void process(uint8_t pin) {
  bool currentState = digitalRead(pin);
  if (currentState == lastPinState[pin]) return;
  unsigned long currentMillis = millis();
  if (currentMillis - lastDebounceTime[pin] < DEBOUNCE_DELAY) return;
  
  uint8_t note = START_NOTE + pin;
  if (currentState == LOW) {
    usbMIDI.sendNoteOn(note, VELOCITY, MIDI_CHANNEL);
  } else {
    usbMIDI.sendNoteOff(note, 0, MIDI_CHANNEL);
  }
  lastPinState[pin] = currentState;
  lastDebounceTime[pin] = currentMillis;
}

void loop() {
  for (uint8_t pin = 0; pin < NUM_DIGITAL_PINS; pin++)
    process(pin);
  // USB MIDI needs to handle incoming messages/flush output
  while (usbMIDI.read()) {}
}