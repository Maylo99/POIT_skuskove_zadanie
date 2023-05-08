// defines pins numbers
const int trigPin = 9;
const int echoPin = 10;
const int  irPin = 7;
int irState = 0;
// defines variables
long duration;
int distance;
void setup() {
  pinMode(irPin, INPUT);  // Sets the irPin as an Input
  pinMode(trigPin, OUTPUT); // Sets the trigPin as an Output
  pinMode(echoPin, INPUT); // Sets the echoPin as an Input
  Serial.begin(9600); // Starts the serial communication
}
void loop() {
 while(true){
    delay(2000);
  irState = digitalRead(irPin);
  //Serial.println(irState);
    // Clears the trigPin
    digitalWrite(trigPin, LOW);
    delayMicroseconds(2);
    // Sets the trigPin on HIGH state for 10 micro seconds
    digitalWrite(trigPin, HIGH);
    delayMicroseconds(10);
    digitalWrite(trigPin, LOW);
    // Reads the echoPin, returns the sound wave travel time in microseconds
    duration = pulseIn(echoPin, HIGH);
    // Calculating the distance
    distance = duration * 0.034 / 2;
    // Prints the distance on the Serial Monitor
    Serial.print("Distance:");
    Serial.print(distance);
    Serial.print(":Ir:");
    Serial.println(irState);
 }
}