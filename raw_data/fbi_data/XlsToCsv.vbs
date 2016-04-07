'On Error Resume Next

Set objFSO = CreateObject("Scripting.FileSystemObject")
objStartFolder = "S:\Projects\exaptive\data\us_cities\fbi_data"

Set objFolder = objFSO.GetFolder(objStartFolder)

Set colFiles = objFolder.Files
For Each objFile in colFiles
	Dim oExcel
	Set oExcel = CreateObject("Excel.Application")
    xlsFile = objStartFolder & "\" & objFile.Name
	
    'csvFile = xlsFile & ".csv"
	tabFile = xlsFile & ".txt"	
	Dim oBook
	Set oBook = oExcel.Workbooks.Open(xlsFile,,True,,,,,,,,,,,,2)
	If Err.Number <> 0 Then
		Err.Clear
	Else
		'oBook.SaveAs csvFile, 6
		oBook.SaveAs tabFile, -4158
		
		oBook.Close False
	End If
	oExcel.Quit	
Next

