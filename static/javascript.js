var papercounter = 1;
var infocounter = 1;
var infosublistcounter = 1;

function addInput(divName){
	var table = document.getElementById(divName);
	var row = table.insertRow();
	var cell1 = row.insertCell(0);
	if (divName == "paperTable"){
	    cell1.innerHTML = "<input type='text' name=ptname>";
	    var cell2 = row.insertCell(1);
	    cell2.innerHTML = "<input type='checkbox' name=ptradio"+ (papercounter+1)+">";
	    papercounter++;
	} else if (divName == "infotable") {
	    cell1.innerHTML = infocounter + 1
	    var cell2 = row.insertCell(1);
	    cell2.innerHTML = "<input type='text' name='infoname'>";
	    var cell3 = row.insertCell(2);
	    cell3.innerHTML = "<input type='text' name='infotext'>";
	    var cell4 = row.insertCell(3);
	    cell4.innerHTML = "<select name='infotype'><option value='0'>Radio Boxes</option><option value='1'>Check Boxes</option><option value='3'>Text entry (1 per line)</option><option value='2'>Text entry (free form)</option></select>";
	    infocounter++
	    
	} else if (divName == "infosublist") {
	    cell1.innerHTML = "<input type='number' name='infosublistid'>";
	    var cell2 = row.insertCell(1);
	    cell2.innerHTML = "<input type='text' name='infosublistentry'>";
	    infosublistcounter++
	}


}
