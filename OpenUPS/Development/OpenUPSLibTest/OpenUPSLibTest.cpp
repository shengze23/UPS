// OpenUPSLibTest.cpp : Defines the entry point for the console application.
//

#include "stdafx.h"
#include <windows.h>
#include <conio.h>
#include "..\OpenUPSLib\OpenUPSLib.h"

int _tmain(int argc, _TCHAR* argv[])
{
	printf("HIT ANY KEY TO EXIT!\n");
	if (UPSOpenDevice(1000))
	{
		printf("UPS opened!\n");
		Sleep(500);	//it's recommended to give a few miliseconds before the first read otherwise the first read might be 0 

		//the library reads the UPS values in every 1000 msec (once per second)
		//therefore is useless to read them faster from here
		
		printf(" firmware: %02d.%02d \n",getUPSVerMajor(),getUPSVerMinor());
		printf(" state: %d\n",getUPSState());
		printf("------------------------------\n");
		
		int state;

		while (!kbhit())
		{
			state = getUPSState();
			
			if (state == 0)
				printf("No device\n");
			else
			{
				switch (state)
				{
				case 1: printf("State: Battery  ");break;
				case 2: printf("State: VIn  ");break;
				case 3: printf("State: only USB  ");break;
				default:printf("State: Error  ");
				}
				printf("POut:%.2f",getUPSOutputPower());
				printf("\n");
				printf("VIN=%.2f ",getUPSVIN());
				printf("VBAT=%.2f ",getUPSVBat());
				printf("VOut=%.2f ",getUPSVOut());
				printf("ACharge=%.2f ",getUPSCCharge());
				printf("ADischg=%.2f ",getUPSCDischarge());
				printf("AIn=%.2f ",getUPSCIn());
				printf("Temp=%.2f\n",getUPSTemperature());
				printf("VCell{");
				for (int i=0;i<6;i++)
					printf("[%d]=%.2f ",i,getUPSVCell(i));
				printf("}\n");
				
			}
			
			Sleep(1000);
		}
		UPSCloseDevice();
	}
	else
	{
		printf("UPS not found!\n");
		_getch();
	}

	return 0;
}

