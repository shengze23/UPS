// The following ifdef block is the standard way of creating macros which make exporting 
// from a DLL simpler. All files within this DLL are compiled with the OPENUPS_EXPORTS
// symbol defined on the command line. this symbol should not be defined on any project
// that uses this DLL. This way any other project whose source files include this file see 
// OPENUPS_API functions as being imported from a DLL, whereas this DLL sees symbols
// defined with this macro as being exported.
#ifdef OPENUPS_EXPORTS
#define OPENUPS_API __declspec(dllexport)
#else
#define OPENUPS_API __declspec(dllimport)
#endif

// This class is exported from the OpenUPS.dll

/** UPSOpenDevice - Open UPS via HID (opens fist one if more connected)
* @param timer - timeperiod for requests (millisecond)
*	Example: timer = 1000 will trigger three HID requests at ~300 msecond, ~600 msecond and ~1000 msecond.
*			This value is not accurate - based on Sleep(5) period.
*			It is provided only to finetune a different request period depending on the user's needs.
*/
extern "C" OPENUPS_API unsigned char UPSOpenDevice(unsigned int timer);
extern "C" OPENUPS_API void UPSCloseDevice();

extern "C" OPENUPS_API unsigned char isUPSConnected();
extern "C" OPENUPS_API float getUPSVIN();
extern "C" OPENUPS_API float getUPSVBat();
extern "C" OPENUPS_API float getUPSVOut();
extern "C" OPENUPS_API float getUPSCCharge();
extern "C" OPENUPS_API float getUPSCDischarge();
extern "C" OPENUPS_API float getUPSCIn();
extern "C" OPENUPS_API float getUPSVCell(int i);
extern "C" OPENUPS_API float getUPSTemperature();
extern "C" OPENUPS_API unsigned char getUPSVerMajor();
extern "C" OPENUPS_API unsigned char getUPSVerMinor();
extern "C" OPENUPS_API unsigned char getUPSState();

extern "C" OPENUPS_API unsigned char getUPSYear();
extern "C" OPENUPS_API unsigned char getUPSMonth();
extern "C" OPENUPS_API unsigned char getUPSDay();
extern "C" OPENUPS_API unsigned char getUPSHour();
extern "C" OPENUPS_API unsigned char getUPSMinute();
extern "C" OPENUPS_API unsigned char getUPSSecond();
extern "C" OPENUPS_API unsigned char getUPSRemainingCapacity();
extern "C" OPENUPS_API unsigned int  getUPSRTE();//if ( getUPSRTE > 0xFFFF)	RTE not known, else RTE = minutes;

extern "C" OPENUPS_API float getUPSOutputPower();

