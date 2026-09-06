Imports System.Runtime.InteropServices
Imports System.Text

Module Module1

    <DllImport("OpenUPSLib.dll", CallingConvention:=CallingConvention.Cdecl)> Function UPSOpenDevice(ByVal timer As Integer) As Byte
    End Function
    <DllImport("OpenUPSLib.dll", CallingConvention:=CallingConvention.Cdecl)> Sub UPSCloseDevice()
    End Sub
    <DllImport("OpenUPSLib.dll", CallingConvention:=CallingConvention.Cdecl)> Function isUPSConnected() As Byte
    End Function
    <DllImport("OpenUPSLib.dll", CallingConvention:=CallingConvention.Cdecl)> Function getUPSVIN() As Single
    End Function
    <DllImport("OpenUPSLib.dll", CallingConvention:=CallingConvention.Cdecl)> Function getUPSVBat() As Single
    End Function
    <DllImport("OpenUPSLib.dll", CallingConvention:=CallingConvention.Cdecl)> Function getUPSVOut() As Single
    End Function
    <DllImport("OpenUPSLib.dll", CallingConvention:=CallingConvention.Cdecl)> Function getUPSCCharge() As Single
    End Function
    <DllImport("OpenUPSLib.dll", CallingConvention:=CallingConvention.Cdecl)> Function getUPSCDischarge() As Single
    End Function
    <DllImport("OpenUPSLib.dll", CallingConvention:=CallingConvention.Cdecl)> Function getUPSCIn() As Single
    End Function
    <DllImport("OpenUPSLib.dll", CallingConvention:=CallingConvention.Cdecl)> Function getUPSVCell(ByVal cnt As Integer) As Single
    End Function
    <DllImport("OpenUPSLib.dll", CallingConvention:=CallingConvention.Cdecl)> Function getUPSTemperature() As Single
    End Function
    <DllImport("OpenUPSLib.dll", CallingConvention:=CallingConvention.Cdecl)> Function getUPSVerMajor() As Byte
    End Function
    <DllImport("OpenUPSLib.dll", CallingConvention:=CallingConvention.Cdecl)> Function getUPSVerMinor() As Byte
    End Function
    <DllImport("OpenUPSLib.dll", CallingConvention:=CallingConvention.Cdecl)> Function getUPSState() As Byte
    End Function
    <DllImport("OpenUPSLib.dll", CallingConvention:=CallingConvention.Cdecl)> Function getUPSRemainingCapacity() As Byte
    End Function
    <DllImport("OpenUPSLib.dll", CallingConvention:=CallingConvention.Cdecl)> Function getUPSOutputPower() As Byte
    End Function

    Sub Main()
        Console.WriteLine("HIT <Esc> TO EXIT!")

        Dim state As Integer

        UPSOpenDevice(1000)
        If (isUPSConnected() = 1) Then
            Console.WriteLine("UPS opened!")
            System.Threading.Thread.Sleep(500) 'it's recommended to give a few miliseconds before the first read otherwise the first read might be 0 

            'the library reads the UPS values in every 1000 msec (once per second)
            'therefore is useless to read them faster from here

            Console.Write(" firmware: ")
            Console.Write(getUPSVerMajor())
            Console.Write(".")
            Console.Write(getUPSVerMinor())
            Console.WriteLine()
            Console.Write(" state: ")
            Console.Write(getUPSState())
            Console.WriteLine()
            Console.WriteLine("------------------------------")
        Else
            Console.WriteLine("UPS not found!")
        End If

        Dim ch As ConsoleKey = ConsoleKey.Backspace 'no matter, just not Esc

        While (ch <> ConsoleKey.Escape)
            If (Console.KeyAvailable) Then
                ch = Console.ReadKey().Key
            End If

            If (isUPSConnected() = 0) Then
                'upsCloseDeviceHandler();//close it only if you do not want auto reconnect
                Console.WriteLine("No device")
            Else
                state = getUPSState()
                If (state = 0) Then
                    Console.WriteLine("No device")
                Else
                    Select Case state
                        Case 1
                            Console.Write("State:Battery ")
                        Case 2
                            Console.Write("State:VIn ")
                        Case 3
                            Console.Write("State:only USB ")
                    End Select
                    Console.Write("VIN=")
                    Console.Write(getUPSVIN())
                    Console.Write(" VBAT=")
                    Console.Write(getUPSVBat())
                    Console.Write(" VOut=")
                    Console.Write(getUPSVOut())
                    Console.Write(" ACharge=")
                    Console.Write(getUPSCCharge())
                    Console.Write(" ADischg=")
                    Console.Write(getUPSCDischarge())
                    Console.WriteLine()
                    Console.Write("Temp=")
                    Console.Write(getUPSTemperature())
                    Console.Write(" ")
                    Console.Write("VCell=")
                    Console.Write(getUPSVCell(0))
                    Console.Write(" ")
                    Console.Write(getUPSVCell(1))
                    Console.Write(" ")
                    Console.Write(getUPSVCell(2))
                    Console.Write(" ")
                    Console.Write(getUPSVCell(3))
                    Console.Write(" ")
                    Console.Write(getUPSVCell(4))
                    Console.Write(" ")
                    Console.Write(getUPSVCell(5))
                    Console.Write(" ")
                    Console.WriteLine()
                End If
            End If
            System.Threading.Thread.Sleep(1000)
        End While
        UPSCloseDevice()
    End Sub

End Module
