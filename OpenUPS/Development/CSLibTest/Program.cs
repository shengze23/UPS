using System;
using System.IO;
using System.Collections.Generic;
using System.Text;
using System.Runtime.InteropServices;

namespace CSLibTest
{
    class Program
    {
        [DllImport("OpenUPSLib.dll", CallingConvention = CallingConvention.Cdecl)]
        public static extern Byte UPSOpenDevice(int timer);
        [DllImport("OpenUPSLib.dll", CallingConvention = CallingConvention.Cdecl)]
        public static extern void UPSCloseDevice();
        [DllImport("OpenUPSLib.dll", CallingConvention = CallingConvention.Cdecl)]
        public static extern Byte isUPSConnected();
        [DllImport("OpenUPSLib.dll", CallingConvention = CallingConvention.Cdecl)]
        public static extern float getUPSVIN();
        [DllImport("OpenUPSLib.dll", CallingConvention = CallingConvention.Cdecl)]
        public static extern float getUPSVBat();
        [DllImport("OpenUPSLib.dll", CallingConvention = CallingConvention.Cdecl)]
        public static extern float getUPSVOut();
        [DllImport("OpenUPSLib.dll", CallingConvention = CallingConvention.Cdecl)]
        public static extern float getUPSCCharge();
        [DllImport("OpenUPSLib.dll", CallingConvention = CallingConvention.Cdecl)]
        public static extern float getUPSCDischarge();
        [DllImport("OpenUPSLib.dll", CallingConvention = CallingConvention.Cdecl)]
        public static extern float getUPSCIn();
        [DllImport("OpenUPSLib.dll", CallingConvention = CallingConvention.Cdecl)]
        public static extern float getUPSVCell(int cnt);
        [DllImport("OpenUPSLib.dll", CallingConvention = CallingConvention.Cdecl)]
        public static extern float getUPSTemperature();
        [DllImport("OpenUPSLib.dll", CallingConvention = CallingConvention.Cdecl)]
        public static extern Byte getUPSVerMajor();
        [DllImport("OpenUPSLib.dll", CallingConvention = CallingConvention.Cdecl)]
        public static extern Byte getUPSVerMinor();
        [DllImport("OpenUPSLib.dll", CallingConvention = CallingConvention.Cdecl)]
        public static extern Byte getUPSState();
        [DllImport("OpenUPSLib.dll", CallingConvention = CallingConvention.Cdecl)]
        public static extern Byte getUPSYear();
        [DllImport("OpenUPSLib.dll", CallingConvention = CallingConvention.Cdecl)]
        public static extern Byte getUPSMonth();
        [DllImport("OpenUPSLib.dll", CallingConvention = CallingConvention.Cdecl)]
        public static extern Byte getUPSDay();
        [DllImport("OpenUPSLib.dll", CallingConvention = CallingConvention.Cdecl)]
        public static extern Byte getUPSHour();
        [DllImport("OpenUPSLib.dll", CallingConvention = CallingConvention.Cdecl)]
        public static extern Byte getUPSMinute();
        [DllImport("OpenUPSLib.dll", CallingConvention = CallingConvention.Cdecl)]
        public static extern Byte getUPSSecond();
        [DllImport("OpenUPSLib.dll", CallingConvention = CallingConvention.Cdecl)]
        public static extern Byte getUPSRemainingCapacity();
        [DllImport("OpenUPSLib.dll", CallingConvention = CallingConvention.Cdecl)]
        public static extern int getUPSRTE();
        [DllImport("OpenUPSLib.dll", CallingConvention = CallingConvention.Cdecl)]
        public static extern float getUPSOutputPower();

        static void Main(string[] args)
        {
            Console.WriteLine("HIT <Esc> TO EXIT!");

	        int state;

	        UPSOpenDevice(1000);
	        if (isUPSConnected() == 1)
	        {
                Console.WriteLine("UPS opened!");
                System.Threading.Thread.Sleep(500);	//it's recommended to give a few miliseconds before the first read otherwise the first read might be 0 

		        //the library reads the UPS values in every 1000 msec (once per second)
		        //therefore is useless to read them faster from here

		        Console.Write(" firmware: ");Console.Write(getUPSVerMajor());Console.Write(".");Console.Write(getUPSVerMinor());Console.WriteLine();
		        Console.Write(" state: ");Console.Write(getUPSState());Console.WriteLine();
		        Console.WriteLine("------------------------------");
	        }
	        else Console.WriteLine("UPS not found!");

            ConsoleKey ch = ConsoleKey.Backspace;//no matter, just not Esc

            while (ch != ConsoleKey.Escape)
	        {
                if (Console.KeyAvailable)
			        ch = Console.ReadKey().Key;

		        if (isUPSConnected() == 0)
		        {
			        //upsCloseDeviceHandler();//close it only if you do not want auto reconnect
			        Console.WriteLine("No device");
		        }
		        else
		        {
			        state = getUPSState();
			        if (state == 0)
				        Console.WriteLine("No device");
			        else
			        {
				        switch (state)
				        {
				        case 1: Console.Write("State:Battery ");break;
				        case 2: Console.Write("State:VIn ");break;
				        case 3: Console.Write("State:only USB ");break;
				        }
				        Console.Write("VIN=");Console.Write(getUPSVIN());
                        Console.Write(" VBAT="); Console.Write(getUPSVBat());
                        Console.Write(" VOut="); Console.Write(getUPSVOut());
                        Console.Write(" ACharge="); Console.Write(getUPSCCharge());
                        Console.Write(" ADischg="); Console.Write(getUPSCDischarge());
                        Console.WriteLine();
                        Console.Write("Temp=");
                        Console.Write(getUPSTemperature()); Console.Write(" ");
                        Console.Write("VCell="); 
                        Console.Write(getUPSVCell(0)); Console.Write(" ");
                        Console.Write(getUPSVCell(1)); Console.Write(" ");
                        Console.Write(getUPSVCell(2)); Console.Write(" ");
                        Console.Write(getUPSVCell(3)); Console.Write(" ");
                        Console.Write(getUPSVCell(4)); Console.Write(" ");
                        Console.Write(getUPSVCell(5)); Console.Write(" ");
                        Console.Write("Cap=");
                        Console.Write(getUPSRemainingCapacity()); Console.Write(" ");
                        Console.Write("RTE=");
                        Console.Write(getUPSRTE()); Console.Write(" ");
                        Console.WriteLine();
			        }
		        }
		        System.Threading.Thread.Sleep(1000);
	        }//while
            
	        UPSCloseDevice();
        }
    }
}
