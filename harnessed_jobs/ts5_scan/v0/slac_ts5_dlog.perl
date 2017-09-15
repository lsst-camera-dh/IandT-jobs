#!/usr/bin/perl
use warnings;
use strict;
use POSIX;
use Getopt::Long;
use IPC::Open3;
use IO::Select;
use Symbol;
use DateTime;
use Time::HiRes qw( gettimeofday tv_interval );
use Scalar::Util qw(looks_like_number);

open(KEY,">","keyence_dlog.log") || die;
my $nkey=0;
open(REB,">","reb_dlog.log") || die;
my $nreb=0;
open(TS7,">","ts7_dlog.log") || die;
my $nts7=0;
open(AER,">","aerotech_dlog.log") || die;
my $naer=0;
open(FLU,">","flushbuffers_dlog.log") || die;
my $nflu=0;

my $keyence_sample_time_settings={"0" => 2.55e-6,
				  "1" => 5e-6,
				  "2" => 10e-6,
				  "3" => 20e-6,
				  "4" => 50e-6,
				  "5" => 100e-6,
				  "6" => 200e-6,
				  "7" => 500e-6,
				  "8" => 1000e-6};

my $keyence_filter_model_settings={"0" => 1,
				   "1" => 4,
				   "2" => 16,
				   "3" => 64,
				   "4" => 256,
				   "5" => 1024,
				   "6" => 4096,
				   "7" => 16384,
				   "8" => 65536,
				   "9" => 262144};

my $pulsescan_ramprate=10.0;

my $usage="USAGE:\t$0 [args]\n".
    "\t[args] are any combination of:\n\n".
    "\t--input_file=<scan_input_file>\n\t\t(e.g., prepared using slac_ts5_metro_scan.perl)\n".
    "\t[--output_filename_root=<output_filename_root>]\n\t\t(output file will only begin with this string)\n".
    "\t[--keyence_sampletime_par=<(0[2.55usec]) | (1[5usec]) | \n".
    "\t\t(2[10usec])  | (3[20usec])  | (4[50usec]) | (5|[100usec]) |\n".
    "\t\t(6[200usec]) | (7[500usec]) | (8[1000usec])>]\n".
    "\t[--keyence_filter_nsample=<(0[x1]) | (1[x4]) | (2[x16]) | \n".
    "\t\t(3[x64])    | (4[x256])   | (5[x1024]) | (6[x4096]) | \n".
    "\t\t(7[x16384]) | (8[x65536]) | (9[x262144])>]\n".
    "\t[--verbose]\n".
    "\t[--keyence_out1_maskpars=out1_max:out1_min]\n".
    "\t[--keyence_out2_maskpars=out2_max:out2_min]\n".
    "\n".
    "\t[--pulsescan_ramprate=<ramprate_for_running_start mm/s2>]";

my $verbose=0;
my $input_file;
my ($keyence_sample_time_ix,$keyence_filter_model_ix,
    $keyence_out_sync_ix,   $keyence_out_storage_ix,
    $keyence_storagemode_ix,$keyence_trigger_ix,
    $nmax_stored_samples)=(5,6,1,1,10,0,50000);
my ($keyence_out1_maskpars,$keyence_out2_maskpars);
my $keyence_head_mask_ix=[1,1];
my $keyence_head_mask_setting=[[+1.0,-1.0],[+5.0,-5.0]];
my $output_filename_root="my_output";
my $incomplete_output;
my $help=0;

GetOptions("keyence_sampletime_par=i" => \$keyence_sample_time_ix,
	   "keyence_filter_nsample=i" => \$keyence_filter_model_ix,
	   "keyence_out1_maskpars=s"  => \$keyence_out1_maskpars,
	   "keyence_out2_maskpars=s"  => \$keyence_out2_maskpars,
	   "pulsescan_ramprate=s"     => \$pulsescan_ramprate,
	   "verbose"                  => \$verbose,
	   "input_file=s"             => \$input_file,
	   "output_filename_root=s"   => \$output_filename_root,
	   "incomplete=s"             => \$incomplete_output,
	   "help"                     => \$help) || 
    die("error in command line arguments! exiting..\n",$usage);

if (0) {
    if (!defined($incomplete_output)) {
	printf "incomplete file not defined.\n";
	exit(0);
    } else {
	printf "incomplete file defined.\n";
	my ($icf,$ipf)=($incomplete_output,$input_file);
	open(ICF,"<",$icf) || die;
	open(IPF,"<",$ipf) || die;
	
	close(ICF);
	close(IPF);
	exit(0);
    }
}

$keyence_head_mask_setting->[0]=[reverse sort {$a<=>$b} 
				 split(':',$keyence_out1_maskpars)] 
    if (defined($keyence_out1_maskpars));
$keyence_head_mask_setting->[1]=[reverse sort {$a<=>$b}
				 split(':',$keyence_out2_maskpars)] 
    if (defined($keyence_out2_maskpars));

die("ERROR - keyence_sampletime_par (".
    $keyence_sample_time_ix.
    ") value is set to an undefined value.\nexiting..\n".$usage)
    if (!defined($keyence_sample_time_settings->{$keyence_sample_time_ix}));
die("ERROR - keyence_filter_nsample (".
    $keyence_filter_model_ix.
    ") is set to an undefined value.\nexiting..\n".$usage)
    if (!defined($keyence_filter_model_settings->{$keyence_filter_model_ix}));

# summarize settings
if ($verbose || $help){
    my $str="";
    $str .= sprintf("$0 settings:\n\n");
    if (!defined($input_file)) {
	$str .= sprintf("\tScan input (plan) file not specified (see usage)\n");
    } else {
	$str .= sprintf("\tWill use scan input (plan) file $input_file\n");
    }
    $str .= sprintf("\tOutput file will look like: %s_<UTC_timestamp>.tnt\n",
		    $output_filename_root);
    $str .= sprintf("\tKeyence sampling time parameter: %d (%g s)\n",
		    $keyence_sample_time_ix,
		    $keyence_sample_time_settings->{$keyence_sample_time_ix});
    $str .= sprintf("\tKeyence filter nsamples in calc: %d (%g samples in calculation)\n",
		    $keyence_filter_model_ix,
		    $keyence_filter_model_settings->{$keyence_filter_model_ix});;
    my $dwelltime=($keyence_sample_time_settings->{$keyence_sample_time_ix}*
		   $keyence_filter_model_settings->{$keyence_filter_model_ix});
    $str .= sprintf("\tTarget dwell time: %g seconds per captured sample\n",$dwelltime);
    $str .= sprintf("\tKeyence OUT1 mask setting: %s (inclusive if descending, exclusive otherwise)\n",
		    join(':',@{$keyence_head_mask_setting->[0]}));
    $str .= sprintf("\tKeyence OUT2 mask setting: %s (inclusive if descending, exclusive otherwise)\n",
		    join(':',@{$keyence_head_mask_setting->[1]}));
    $str .= sprintf("\n\tCurrent pulsescan ramprate settings will force \"running start\" distances to be:\n");
    $str .= sprintf("\t\t%.2f mm (for 1mm sampling and 0.95 duty cycle)\n",pow((1*0.95)/$dwelltime,2)/(2*$pulsescan_ramprate));
    $str .= sprintf("\t\t%.2f mm (for 4mm sampling and 0.95 duty cycle)\n",pow((4*0.95)/$dwelltime,2)/(2*$pulsescan_ramprate));
    if ($help) {
	$str .= sprintf("\n\tIf these running start distances seem excessive, consider adjusting\n\t\t--keyence_sampletime_par to correspond to a longer duration,\n\t\t--keyence_filter_nsample to correspond to a larger number of\n\t\t  samples per calculation, or adjust\n\t\t--pulsescan_ramprate to correspond to a larger acceleration.\n");
	$str .= sprintf("\n\tIf none of these options are suitable, consider preparing\n\ta higher density scan input (plan) file before continuing.\n");
    } else {
	$str .= sprintf("\n\tMoving ahead with the plan..\n");
    }
    printf STDERR "%s\n",$str;
}

if ($help) {
    printf STDERR "%s\n\n",$usage;
    exit;
}

my $instr={};
my $save_settings=0;

$instr->{"meas"}={"target"  => "metrology/Measurer",
		  "channel" => "keyenceChat",
		  "dlog"    => \&kchatter,
		  "save_pars" => "this.txt",
		  "startup" => 1};

$instr->{"posn"}={"target"  => "metrology/Positioner",
		  "channel" => "aerotechChat",
		  "dlog"    => \&achatter,
		  "startup" => 1};

$instr->{"REB0_CCDTemp0"}={"target"  => "ts8-raft/R00.Reb0.CCDTemp0",
			   "channel" => "getValue",
			   "dlog"    => \&rebchatter,
			   "startup" => 1};

$instr->{"REB1_CCDTemp1"}={"target"  => "ts8-raft/R00.Reb1.CCDTemp1",
			   "channel" => "getValue",
			   "dlog"    => \&rebchatter,
			   "startup" => 1};

$instr->{"REB2_CCDTemp2"}={"target"  => "ts8-raft/R00.Reb2.CCDTemp2",
			   "channel" => "getValue",
			   "dlog"    => \&rebchatter,
			   "startup" => 1};

$instr->{"CryoPlateTemp"}={"target"  => "ts7-1/CryoPlate",
			   "channel" => "getValue",
			   "dlog"    => \&ts7chatter,
			   "startup" => 1};

# more setup
foreach my $ky (keys %{$instr}) {
    $instr->{$ky}->{"prepend"}=join(" ",$instr->{$ky}->{"target"},$instr->{$ky}->{"channel"});
    printf "for key %s prepend is %s\n",$ky,$instr->{$ky}->{"prepend"};
}

printf STDERR "keys of instr: %s\n",join(',',keys %{$instr}) 
    if ($verbose);

my ($snd,$ret);
my ($pid,$sel,$fh);

do {
    ($pid,$sel,$fh)=shell_command_console($instr);
} until ($pid != 0);
# link established
{
    printf STDERR "connection established!\nexiting..\n";
#    exit;
}
my $ap=aero_pos($sel,$fh,$instr->{"posn"},["X","Y","Z"]);
printf STDERR "return values: %s\n",join(':',@{$ap}) 
    if ($verbose);

my $tk=keyence_pos($sel,$fh,$instr->{"meas"});
printf STDERR "return values: %s\n",join(':',@{$tk})
    if ($verbose);

# command aerotech controller to operate in NOWAIT mode
{
    my $posn=$instr->{"posn"};
    # stop any program that may be running in thread 1
    my $ret=$posn->{"dlog"}($sel,$fh,$posn->{"prepend"},posnquot("TASKSTATE 1"));
    if ($ret =~ /\%3/) {
	printf STDERR "stopping a running program...\t"
	    if ($verbose);
	$ret=$posn->{"dlog"}($sel,$fh,$posn->{"prepend"},posnquot("PROGRAM STOP 1"));
	sleep(3);
	printf STDERR "done.\n"
	    if ($verbose);
    }
    # stop motor movement if moving
    if (planestatus($instr->{"posn"},1,0.0)) {
	printf STDERR "stopping a moving motor...\t"
	    if ($verbose);
 	select(undef,undef,undef,0.5);
	$ret=$instr->{"posn"}->{"dlog"}($sel,$fh,$instr->{"posn"}->{"prepend"},
					posnquot("ABORT X Y Z"));
 	do {} while (planestatus($instr->{"posn"},1,0.15));
	printf STDERR "done.\n"
	    if ($verbose);
    }

    $posn->{"dlog"}($sel,$fh,$posn->{"prepend"},posnquot("WAIT MODE NOWAIT"));
    # and then read parameters queried by GETMODE
    my $r;
    my $retlist=[];
    foreach my $i (0..12) {
	$r=$posn->{"dlog"}($sel,$fh,$posn->{"prepend"},posnquot("GETMODE $i"));
	($retlist->[$i]) = ($r =~ /%(\S+)/);
	$retlist->[$i] = "gotmode ".$i." = ".$retlist->[$i];
    }
    printf STDERR "%s\n",join("\n",@{$retlist})
	if ($verbose);
}

my $dwelltime;
# set keyence timing parameters here
{
    my $keyence_sample_time={"cmd" => "SW,CA,%1d",
			     %{$keyence_sample_time_settings}};

    my $keyence_filter_model={"cmd" => "SW,OC,%02d,0,%1d",
			      %{$keyence_filter_model_settings}};

    my $keyence_sync_setting={"cmd" => "SW,OJ,%02d,%1d",
			       "0" => 0,
			       "1" => 1};
    my $keyence_storage_setting={"cmd" => "SW,OK,%02d,%1d",
				 "0" => 0,
				 "1" => 1};
    my $keyence_storagemode_setting={"cmd" => "SW,CF,%07d,%02d",
				     "0" => 1,
				     "1" => 2,
				     "2" => 5,
				     "3" => 10,
				     "4" => 20,
				     "5" => 50,
				     "6" => 100,
				     "7" => 200,
				     "8" => 500,
				     "9" => 1000,
				     "10"=> "synchronous input"};
    my $keyence_trigger_setting={"cmd" => "SW,OE,M,%02d,%1d",
				 "0" => 1,
				 "1" => 2};
    my $keyence_mask_setting={"cmd" => "SW,HF,%02d,%1d,%+07d,%+07d",
			      "0" => 0,
			      "1" => 1};


    my $snd;
    my $cmds=[];
    $snd="Q0";
    push(@{$cmds},$snd);
    $snd=sprintf($keyence_sample_time->{"cmd"},$keyence_sample_time_ix);
    push(@{$cmds},$snd);

    $snd=sprintf($keyence_storagemode_setting->{"cmd"},
		 $nmax_stored_samples,$keyence_storagemode_ix);
    push(@{$cmds},$snd);

    foreach my $out_ix (1,2) {
	$snd=sprintf($keyence_trigger_setting->{"cmd"},
		     $out_ix,$keyence_trigger_ix);
	push(@{$cmds},$snd);
	$snd=sprintf($keyence_filter_model->{"cmd"},
		     $out_ix,$keyence_filter_model_ix);
	push(@{$cmds},$snd);
	$snd=sprintf($keyence_sync_setting->{"cmd"},
		     $out_ix,$keyence_out_sync_ix);
	push(@{$cmds},$snd);
	$snd=sprintf($keyence_storage_setting->{"cmd"},
		     $out_ix,$keyence_out_storage_ix);
	push(@{$cmds},$snd);
	$snd=sprintf($keyence_mask_setting->{"cmd"},
		     $out_ix,$keyence_head_mask_ix->[$out_ix-1],
		     reverse sort {$a<=>$b}
		     (100*$keyence_head_mask_setting->[$out_ix-1]->[0],
		      100*$keyence_head_mask_setting->[$out_ix-1]->[1]));
	push(@{$cmds},$snd);
    }
    $snd="R0";
    push(@{$cmds},$snd);

    my $rets=kphrase($sel,$fh,$instr->{"meas"}->{"prepend"},$cmds);
    foreach my $i (0..$#{$cmds}) {
	printf STDERR "Psent: %-20s\tPret: %-20s\n",$cmds->[$i],$rets->[$i]
	    if ($verbose);
    }

    if (1) {
	if (defined($instr->{"meas"}->{"save_pars"})) {
	    open(F,">",$instr->{"meas"}->{"save_pars"}) || die;
	}
	my ($snt,$rtn)=get_settings($sel,$fh);
	foreach my $i ( 0..$#{$snt} ) {
	    printf STDERR "sent: %-20s\tret: %-20s\n",$snt->[$i],$rtn->[$i]
		if ($verbose);
	    printf F "%-20s\n",$rtn->[$i] if (defined($instr->{"meas"}->{"save_pars"}));
	}
	close(F) if (defined($instr->{"meas"}->{"save_pars"}));
    }
    $dwelltime = ($keyence_filter_model->{$keyence_filter_model_ix}*
		  $keyence_sample_time->{$keyence_sample_time_ix});
    printf STDERR "dwelltime = %g\n",$dwelltime
	if ($verbose);
}

# settings received.

exit if (!defined($input_file));

my $timestr=timestr();

open(GG,">",$output_filename_root."_".$timestr.".tnt") || die;
printf GG "# measurement begun at UTC %s\n",$timestr;
printf GG "# input file: %s\n",$input_file;

if (defined($instr->{"meas"}->{"save_pars"})) {
    open(FF,"<",$instr->{"meas"}->{"save_pars"}) || die;
    while ($_=<FF>) {
	chomp;
	printf GG "# %s\n",$_;
    }
    close(FF);
}
my $starttime=[gettimeofday()];
my @aero_cols=("aero_x","aero_y","aero_z");
my @keyence_cols=("key_z1","key_z2");
my @bookkeeping_cols=("timestamp","label");
my @temperature_cols;
@temperature_cols=("REB0_CCDTemp0","REB1_CCDTemp1","REB2_CCDTemp2");
@temperature_cols=("CryoPlateTemp");
my @output_cols=(@aero_cols,@keyence_cols,@temperature_cols,@bookkeeping_cols);

printf GG "dat\n%s\n",join("\t",@output_cols);
# specify INPOS
my $posn=$instr->{"posn"};
my $tmp=$posn->{"dlog"}($sel,$fh,$posn->{"prepend"},posnquot("WAIT MODE NOWAIT"));
printf STDERR "tmp=%s\n",$tmp
    if ($verbose);
$posn->{"dlog"}($sel,$fh,$posn->{"prepend"},posnquot("RAMP MODE RATE"));
my $result;
my $last_result;
my $label;
my $move_instructions={"F" => 10,"ramprate" => 1,"scurve" => 10};
$move_instructions={"F" => 100,"ramprate" => 10,"scurve" => 7};


my $inputfile_nlines=`wc -l $input_file`;
$inputfile_nlines = (split(' ',$inputfile_nlines))[0];
chomp $inputfile_nlines;

open(F,"<",$input_file) || die;

my $inputfile_lineno=0;
my %temperature=();

while (my $line=<F>) {
    printf STDERR "progress: %s/%s (%.1f %% complete)\n",$inputfile_lineno,$inputfile_nlines,$inputfile_lineno*100.0/$inputfile_nlines 
	if ($verbose && ($inputfile_lineno%5==0));
    $inputfile_lineno++;
    next if ($line =~ /^no/);
    if ($line =~ /^!/) {
	# update any required temperature measurements
	foreach my $tchan (@temperature_cols) {
	    my $T=$instr->{$tchan}->{"dlog"}($sel,$fh,$instr->{$tchan}->{"prepend"},"");
	    $temperature{$tchan}=sprintf("%7.2f",$T);
	}
	if ($line =~ /TF/) {
	    # this is a transformation spec that was used in generating
	    # this measurement plan file. echo to output.
	    my ($transform_spec)=($line =~ /!\s*(\S.*)$/);
	    printf GG "# %s\n",$transform_spec;
	}
	if ($line =~ /label/) {
	    ($label) = ($line =~ /label (\S+)/);
	}
	if ($line =~ /ADJUST/) {
	    # do a LINEAR movement on that axis
	    my ($adj_axis,$delta) = ($line =~ /ADJUST (\S+) (\S+)/);
	    my $posn=$instr->{"posn"};
	    $posn->{"dlog"}($sel,$fh,$posn->{"prepend"},
			    posnquot(sprintf("LINEAR %s %f F 0.5",$adj_axis,$delta)));
	    printf "moving relative axis %s by %f\n",$adj_axis,$delta;
	    do {
		printf ".";
	    } while (planestatus($instr->{"posn"},1,0.15));
	    printf "\n";
	}
	if ($line =~ /WAIT/) {
	    # pause
	    my ($wait_time) = ($line =~ /WAIT (\S+)/);
	    printf "pausing for %s seconds..",$wait_time;
	    select(undef,undef,undef,$wait_time);
	    printf "\n";
	    # and continue..
	}
	if ($line =~ /SCAN/) {
	    my ($n,$dutycycle) = ($line =~ /SCAN\s+n=(\d+)\s+dc=([.\d]+)/);
	    $_=<F>;chomp;
	    $inputfile_lineno++;
	    my ($x0,$y0)=split(' ');
	    $_=<F>;chomp;
	    $inputfile_lineno++;
	    my ($x1,$y1)=split(' ');
	    printf STDERR "label=%s n=%d dutycycle=%g start=(%g,%g) end=(%g,%g)\n",$label,$n,$dutycycle,$x0,$y0,$x1,$y1
		if ($verbose);
	    my $ap=aero_pos($sel,$fh,$instr->{"posn"},["Z"]);

	    my ($headings,$retval)=ts5_pulsescan({
		"instr"     => $instr,
		"nsamp"     => $n,
		"dutycycle" => $dutycycle,
		"ramprate"  => $pulsescan_ramprate,
		"from_pos"  => [$x0,$y0],
		"to_pos"    => [$x1,$y1]});

	    my %output=();
	    foreach my $ix (0..$#{$retval->{"key_z1"}}) {
		@output{@aero_cols}=($retval->{"prog_x"}->[$ix],
				     $retval->{"prog_y"}->[$ix],
				     sprintf("%.4f",$ap->[0]));
		@output{@keyence_cols}=($retval->{"key_z1"}->[$ix],
					$retval->{"key_z2"}->[$ix]);
		@output{@temperature_cols}=@temperature{@temperature_cols};
		@output{"timestamp","label"}=
		    ($retval->{"timestamp"}->[$ix],$label);
		printf GG "%s\n",join(' ',@output{@output_cols});
	    }
	}
	next;
    }
    chomp($line);
    my ($x,$y) = split(' ',$line);
    ($move_instructions->{"X"},$move_instructions->{"Y"})=($x,$y);
    move_to($move_instructions);
    do {} while(planestatus($posn,1,0.15));
    # rather than rely on dwell command, use select()
#	$tmp=$posn->{"dlog"}($sel,$fh,$posn->{"prepend"},posnquot(sprintf("DWELL %g",$dwelltime)));
    my $nsample=($label =~ /REF/)?10:1;
    my $iter=0;
    do {
	select(undef,undef,undef,$dwelltime);
	# and read keyence values - should be settled by now..
	my $tk=keyence_pos($sel,$fh,$instr->{"meas"});
	my $ap=aero_pos($sel,$fh,$instr->{"posn"},["X","Y","Z"]);
	my %output=();
	@output{@aero_cols}=@{$ap};
	@output{@keyence_cols}=@{$tk};
	@output{@temperature_cols}=@temperature{@temperature_cols};
	@output{"timestamp","label"}=(tv_interval($starttime,[gettimeofday()]),$label);
	printf GG "%s\n",join(' ',@output{@output_cols});
	$iter++;
    } while ($iter<$nsample);
}
$timestr=timestr();
printf GG "# measurement completed at UTC %s\n",$timestr;
close(GG);

exit;

sub shell_command_console {
    my ($instr)=@_;
    my ($write,$read,$error);
    my $cmd="/lsst/ccs/dev/bin/ShellCommandConsole";

    my $selwrite=IO::Select->new();
    my $selread =IO::Select->new();
    my $selerror=IO::Select->new();
    my $selany  =IO::Select->new();
    my $sel={"WRITE"=>$selwrite,	     "READ" =>$selread,
	     "ERROR"=>$selerror,	     "ANY"  =>$selany};

    $error = gensym();
    my $pid=open3($write,$read,$error,$cmd);

#    $SIG{CHLD} = sub {
#	print STDERR "REAPER: status $? on $pid\n" if waitpid($pid,0)>0;
#    };

    $selwrite->add($write);

    $selread->add($read);
    $selerror->add($error);

    $selany->add($read);
    $selany->add($error);

    my $fh ={"WRITE"=>$write,"READ" =>$read,"ERROR"=>$error};
    
    if (1) {
 	my $svfh;
 	$svfh = select($write); $|=1; select($svfh);
 	$svfh = select($read);  $|=1; select($svfh);
 	$svfh = select($error); $|=1; select($svfh);
 	$svfh = select(STDOUT); $|=1; select($svfh);
     }

    printf STDERR "connecting to ShellCommandConsole "
	if ($verbose);

    # block until ready to read. this is also what apparently causes program to stop if
    # launched in background.

    do {
	select(undef,undef,undef,0.1);
	printf STDERR "."
	    if ($verbose);
    } until(flush_read_buffers($sel));

    select(undef,undef,undef,12);
    flush_read_buffers($sel);


    printf STDERR "here we go!\n"
	if ($verbose);

    # turn off monitoring (well, GUI won't work so well without it)
    # if metrology channels aren't monopolized, it seems to keep
    # sockets alive, which will preclude restarting the subsystem.
    # DONT monopolize for now, it seemed to work better in the past.
    monopolize_channels($sel,$fh) if (0);
    
    foreach my $ky ( keys %{$instr} ) {
	next if (!$instr->{$ky}->{"startup"});
	printf STDERR "testing for $ky.\n"
	    if ($verbose);
	my $pre=$instr->{$ky}->{"prepend"};
	if ($ky eq "posn") {
	    my $snd=posnquot("PSOCONTROL X RESET"); # need to send this anyway
	    my $ret=$instr->{$ky}->{"dlog"}($sel,$fh,$pre,$snd);
	    $instr->{$ky}->{"comm_established"}=1;
	    if ($ret !~ /\%/) {
		$instr->{$ky}->{"comm_established"}=0;
		last;
	    }
	}
	if ($ky eq "meas") {
	    my ($snd0,$ret0);
	    my ($snd1,$ret1);
	    $snd0="Q0";
	    $ret0=$instr->{$ky}->{"dlog"}($sel,$fh,$pre,$snd0);
	    $snd1="R0";
	    $ret1=$instr->{$ky}->{"dlog"}($sel,$fh,$pre,$snd1);
	    $instr->{$ky}->{"comm_established"}=1;
	    if ($snd1 ne $ret1) {
		$instr->{$ky}->{"comm_established"}=0;
		last;
	    }
	}
	if ($ky =~ /REB/) {
	    my ($snd,$ret);
	    $snd="";
	    $ret=$instr->{$ky}->{"dlog"}($sel,$fh,$pre,$snd);
	    $instr->{$ky}->{"comm_established"}=1;
	    if (! looks_like_number($ret)) {
		$instr->{$ky}->{"comm_established"}=0;
		last;
	    }
	}
	if ($ky =~ /Cryo/) {
	    my ($snd,$ret);
	    $snd="";
	    $ret=$instr->{$ky}->{"dlog"}($sel,$fh,$pre,$snd);
	    $instr->{$ky}->{"comm_established"}=1;
	    if (! looks_like_number($ret)) {
		$instr->{$ky}->{"comm_established"}=0;
		last;
	    }
	}
    }
    # now evaluate whether to close everything or proceed.
    my $quit=0;
    foreach my $ky ( keys %{$instr} ) {
	next if (!$instr->{$ky}->{"startup"});
	$quit=1 if ($instr->{$ky}->{"startup"} && 
		    (!$instr->{$ky}->{"comm_established"}));
    }

    if ($quit) {
	close($fh->{"WRITE"});
	waitpid($pid,1);
	$pid=0;
	printf STDERR "will try establishing link to shell command console again...\n"
	    if ($verbose);
    } else {
	printf STDERR "link established.\n"
	    if ($verbose);
    }
    return($pid,$sel,$fh);
}

sub kchatter {
    my ($sel,$fh,$prepend,$cmd)=@_;
    # send out command
    my $snd=join(" ",$prepend,$cmd);
    flush_read_buffers($sel);
    syswrite($fh->{"WRITE"},$snd."\n");
    do {} until ($sel->{"READ"}->can_read(0));
    select(undef,undef,undef,0.05); # 50msec additional
    my $ret = readline($fh->{"READ"});
#    do {
	$ret .= readline($fh->{"READ"});
#    } while ($sel->{"READ"}->can_read(0));

    {
	printf KEY "%d ---\n",$nkey;
	printf KEY "%s",$ret;
	$nkey++;
    }

    my @rets=split("\n",$ret);
    # arbitrary I know, but there's not a great way to check for return strings
    # coming from keyence controller. let the last return be interpreted
    # as return value from Keyence controller.
    my ($echoed_command,$ret_val)=@rets[0,$#rets];
    
    if (($ret_val =~ /^ER/) &&
	($echoed_command !~ "Q0") &&
	($echoed_command !~ "R0")) {
	printf STDERR "kchatter:\n";
	printf STDERR ("echoed command was %s but return value was %s\n",
		       $echoed_command,$ret_val);
	printf STDERR "exiting..\n";
	exit(1);
    }
    $ret_val;
}

sub monopolize_channels {
    my ($sel,$fh)=@_;
    flush_read_buffers($sel);
    my $snd;
    $snd="metrology change publish-data taskPeriodMillis 0";
    syswrite($fh->{"WRITE"},$snd."\n");
    $snd="metrology change monitor-publish taskPeriodMillis 0";
    syswrite($fh->{"WRITE"},$snd."\n");
    
    do {} until ($sel->{"READ"}->can_read(0));
    select(undef,undef,undef,0.05); # 50msec additional
    my $ret = readline($fh->{"READ"});
    $ret .= readline($fh->{"READ"});
    printf STDERR "monopolize: received echoed commands:\n$ret\n";
    flush_read_buffers($sel);
}

sub rebchatter {
    my ($sel,$fh,$prepend,$cmd)=@_;
    $cmd=""; # getting temperature doesn't require an argument, since 
    # getValue is already part of $prepend
    my $snd=join(" ",$prepend,$cmd);
    flush_read_buffers($sel);
    syswrite($fh->{"WRITE"},$snd."\n");
    do {} until ($sel->{"READ"}->can_read(0));
    my $ret = readline($fh->{"READ"});
#    do {
    $ret .= readline($fh->{"READ"});
#    } while ($sel->{"READ"}->can_read(0));

    {
	printf REB "%d ---\n",$nreb;
	printf REB "%s",$ret;
	$nreb++;
    }

    my @rets=split("\n",$ret);
    my ($echoed_command,$ret_val)=@rets[0,$#rets];
    if ($ret_val =~ /Error/) {
	printf STDERR ("REB CHATTER: sent %s received %s\n".
		       "proceeding with caution.\n",
		       $echoed_command,$ret_val);
    }
    $ret_val;
}

sub ts7chatter {
    my ($sel,$fh,$prepend,$cmd)=@_;
    $cmd=""; # getting temperature doesn't require an argument, since 
    # getValue is already part of $prepend
    my $snd=join(" ",$prepend,$cmd);
    flush_read_buffers($sel);
    syswrite($fh->{"WRITE"},$snd."\n");
    do {} until ($sel->{"READ"}->can_read(0));
    my $ret = readline($fh->{"READ"});
#    do {
    $ret .= readline($fh->{"READ"});
#    } while ($sel->{"READ"}->can_read(0));

    {
	printf TS7 "%d ---\n",$nts7;
	printf TS7 "%s",$ret;
	$nts7++;
    }

    my @rets=split("\n",$ret);
    my ($echoed_command,$ret_val)=@rets[0,$#rets];
    if ($ret_val =~ /Error/) {
	printf STDERR ("TS7 CHATTER: sent %s received %s\n".
		       "proceeding with caution.\n",
		       $echoed_command,$ret_val);
    }
    $ret_val;
}

sub achatter {
    my ($sel,$fh,$prepend,$cmd)=@_;
    # send out command
    my $snd=join(" ",$prepend,$cmd);
    flush_read_buffers($sel);
    syswrite($fh->{"WRITE"},$snd."\n");
    do {} until ($sel->{"READ"}->can_read(0));
    select(undef,undef,undef,0.05); # 50msec additional
    my $ret = readline($fh->{"READ"});
#    do {
	$ret .= readline($fh->{"READ"});
#    } while ($sel->{"READ"}->can_read(0));

    {
	printf AER "%d ---\n",$naer;
	printf AER "%s",$ret;
	$naer++;
    }

    my ($echoed_command,$ret_val)=split("\n",$ret);
    # but look for the right form for $ret_val, can avoid unnecessary crashes
    foreach my $rv (split("\n",$ret)) {
	$ret_val=$rv if ($rv =~ /^%/);
	last;
    }
    if ($ret_val !~ /^%/) {
	printf STDERR "achatter:\n";
	printf STDERR ("echoed command was %s but return value was %s\n",
		       $echoed_command,$ret_val);
	printf STDERR "exiting..\n";
	exit(1);
    }
    $ret_val;
}

sub kphrase {
    my ($sel,$fh,$prepend,$cmds)=@_;
    my $send_at_a_time=10;
    printf STDERR "entering kphrase send-at-a-time = %d.\n",$send_at_a_time
	if ($verbose);
    # send out command
    my $retstring="";
    printf STDERR "sending kphrase: %s\n",join(' ',@{$cmds})
	if ($verbose);

    my $sat=0;
    my $rets=[];
    my $ret_vals=[];
    my $echoed_command;
    my $i=0;
    my $j=0;

    flush_read_buffers($sel);

    foreach my $ix (0..$#{$cmds}) {
	my $cmd=$cmds->[$ix];
	my $snd=join(" ",$prepend,$cmd);
	syswrite($fh->{"WRITE"},$snd."\n");
	$j++;
	next if (($j<$send_at_a_time) && ($ix<$#{$cmds}));
	# if control arrives here, need to read $j*2 return lines
	printf STDERR "finished sending.\n" if ($verbose && ($ix == $#{$cmds}));

	while ($j>0) {
	    do {} until ($sel->{"READ"}->can_read(0));
	    $rets->[$i]  = readline($fh->{"READ"});
	    do {} until ($sel->{"READ"}->can_read(0));
	    $rets->[$i] .= readline($fh->{"READ"});
	    ($echoed_command,$ret_vals->[$i])=split("\n",$rets->[$i]);
	    $echoed_command=(split(' ',$echoed_command))[2];
	    if ($echoed_command ne $cmds->[$i]) {
		printf STDERR "WARNING!! echo returned something else:\n$echoed_command\nexpected:\n$cmd\n"
		    if ($verbose);
	    }
	    if (($ret_vals->[$i] =~ /^ER/) &&
		($echoed_command ne "Q0") &&
		($echoed_command ne "R0")) {
		printf STDERR "Keyence dialog error:\n";
		printf STDERR "echoed command %s ",$echoed_command;
		printf STDERR "but received %s\n",$ret_vals->[$i];
		printf STDERR "exiting..\n";
		exit;
	    }
	    printf STDERR "got %d/%d (%s).\n",$i,$#{$cmds},$echoed_command
		if ($verbose);
	    $i++;
	    $j--;
	}
    }
    printf STDERR "exiting kphrase.\n"
	if ($verbose);
    $ret_vals;
}

sub get_settings {
    my ($sel,$fh)=@_;
    my $cmds=[];
    push(@{$cmds},"Q0"); # send this right before kphrase
    push(@{$cmds},"DR");
    foreach my $head ("01","02") {
    }
    foreach my $output ("01","02") {
	push(@{$cmds},"SR,LM,".$output); # output number
	push(@{$cmds},"SR,HA,M,".$output); # head number assumed to be equal to output number
	push(@{$cmds},"SR,HA,R,".$output);
	push(@{$cmds},"SR,HB,M,".$output);
	push(@{$cmds},"SR,HB,B,".$output);
	push(@{$cmds},"SR,HC,N,".$output);
	push(@{$cmds},"SR,HC,L,".$output);
	push(@{$cmds},"SR,HE,".$output); 
	push(@{$cmds},"SR,HF,".$output); 
	push(@{$cmds},"SR,HG,".$output); 
	push(@{$cmds},"SR,HH,".$output); 
	push(@{$cmds},"SR,HI,".$output); 
	push(@{$cmds},"SR,HJ,".$output); 
	push(@{$cmds},"SR,OA,H,".$output);
	push(@{$cmds},"SR,OA,T,".$output);
	push(@{$cmds},"SR,OA,C,".$output);
	push(@{$cmds},"SR,OA,M,".$output);
	push(@{$cmds},"SR,OB,".$output);
	push(@{$cmds},"SR,OC,".$output);
	push(@{$cmds},"SR,OD,".$output);
	push(@{$cmds},"SR,OE,M,".$output);
	push(@{$cmds},"SR,OF,".$output);
	push(@{$cmds},"SR,OG,".$output);
	push(@{$cmds},"SR,OH,".$output);
	push(@{$cmds},"SR,OI,".$output);
	push(@{$cmds},"SR,OJ,".$output);
	push(@{$cmds},"SR,OK,".$output);
    }
    push(@{$cmds},"SR,CA");
    push(@{$cmds},"SR,CB");
    push(@{$cmds},"SR,CD");
    push(@{$cmds},"SR,CE");
    push(@{$cmds},"SR,CF");
    foreach my $chno ("01","02") {
	push(@{$cmds},"SR,CG,".$chno);
    }
    push(@{$cmds},"SR,CH");
    push(@{$cmds},"SR,EE");
    push(@{$cmds},"SR,EF");
    push(@{$cmds},"SR,EG");
    push(@{$cmds},"SR,EH,I");
    push(@{$cmds},"SR,EH,M");
    push(@{$cmds},"SR,EH,G");
    push(@{$cmds},"R0"); # send this right after kphrase
    # use the global scope $instr to look up the prepend string for metrology/Measurer
#    kchatter($sel,$fh,$instr->{"meas"}->{"prepend"},"Q0");
    my $rets=kphrase($sel,$fh,$instr->{"meas"}->{"prepend"},$cmds);
#    kchatter($sel,$fh,$instr->{"meas"}->{"prepend"},"R0");
    return($cmds,$rets);
}

sub exequot {
    my ($str)=@_;
    return(posnquot("PROGRAM RUN 1,\"\"$str\"\""));
}

sub posnquot {
    my ($str)=@_;
    return("\"\'".$str."\'\"");
}

sub psostatus {
    my ($sel,$fh,$posn,$flag)=@_;
    my $tmp=$posn->{"dlog"}($sel,$fh,$posn->{"prepend"},
			    posnquot("PSOSTATUS X"));
    ($tmp) = ($tmp =~ /\%(\S+)/);
    $tmp;
}

sub aero_pos {
    my ($sel,$fh,$posn,$axes)=@_;
    my @result=();
    foreach my $ax (@{$axes}) {
	my $tmp=$posn->{"dlog"}($sel,$fh,$posn->{"prepend"},
				posnquot("PFBK ".$ax));
	if (1) { # formatted nicely
	    my ($ap)=($tmp =~ /\%(\S+)/);
	    push(@result,sprintf("%.4f",$ap));
	} else { # verbatim, no assumptions
	    push(@result,($tmp =~ /\%(\S+)/));
	}
    }    
    [@result];
}

sub keyence_pos {
    my ($sel,$fh,$meas)=@_;
    my @result=();
    my $tmp;
    do {
	$tmp=$meas->{"dlog"}($sel,$fh,$meas->{"prepend"},"MA");
#    } until (1); # this was for using peak-hold etc runs
    } until ($tmp !~ /XXX/);
    return( [(split(',',$tmp))[1,2]] );
}

sub move_to {
    my $target=$_[0];
    my $axis_list=["X","Y","Z"];
    my $current={};
    my $this=aero_pos($sel,$fh,$instr->{"posn"},$axis_list);
    my $i=0;
    foreach my $ax (@{$axis_list}) {
	$current->{$ax}=$this->[$i];
	$i++;
    }
    printf STDERR "current: $current target: $target\n"
	if ($verbose);
    printf STDERR "current: %s target: %s\n",join(' ',%{$current}),join(' ',%{$target})
	if ($verbose);
    my %a=();
    foreach my $ky ( (keys %{$current}, keys %{$target})) {
	$a{$ky}=1;
    }
    my $new_axis_list=[];
    my $new_coord_list=[];
    my $posn=$instr->{"posn"};
    my $aero_command="SCURVE ";
    if (defined($target->{"scurve"})) {
	$aero_command .= sprintf("%g",$target->{"scurve"});
	$posn->{"dlog"}($sel,$fh,$posn->{"prepend"},posnquot($aero_command));
    }

    $aero_command="RAMP RATE ";
    if (defined($target->{"ramprate"})) {
	$aero_command .= sprintf("%g",$target->{"ramprate"});
	$posn->{"dlog"}($sel,$fh,$posn->{"prepend"},posnquot($aero_command));
    }
    $aero_command="RAMP DIST ";
    if (defined($target->{"rampdist"})) {
	$aero_command .= sprintf("%g",$target->{"rampdist"});
	$posn->{"dlog"}($sel,$fh,$posn->{"prepend"},posnquot($aero_command));
    }
    $aero_command="RAMP TIME ";
    if (defined($target->{"ramptime"})) {
	$aero_command .= sprintf("%g",$target->{"ramptime"});
	$posn->{"dlog"}($sel,$fh,$posn->{"prepend"},posnquot($aero_command));
    }

    $aero_command="LINEAR";
    foreach my $uniq_key (sort keys %a) {
	if (defined($current->{$uniq_key}) && defined($target->{$uniq_key})) {
	    # will examine and possibly change this coordinate.
	    push(@{$new_axis_list},$uniq_key);
	    push(@{$new_coord_list},sprintf("%g",$target->{$uniq_key}-$current->{$uniq_key}));
	    $aero_command .= " ".$uniq_key." ".sprintf("%g",$target->{$uniq_key}-$current->{$uniq_key});
	}
    }
    # see if maximum speed was specified
    if (defined($target->{"F"})) {
	$aero_command .= " F ".sprintf("%g",$target->{"F"});
    } else {
	# don't specify speed
    }
    printf STDERR "new axis: %s\nnew coords: %s\n",join(' ',@{$new_axis_list}),join(' ',@{$new_coord_list})
	if ($verbose);
    my $tmp=$posn->{"dlog"}($sel,$fh,$posn->{"prepend"},posnquot($aero_command));
#    printf STDERR "tried to send: $aero_command return string: %s\n",$tmp;
}

sub planestatus {
    my ($posn,$flag,$pause)=@_;
    my $result=$posn->{"dlog"}($sel,$fh,$posn->{"prepend"},
			       posnquot("PLANESTATUS 0"));
    select(undef,undef,undef,$pause);
    my ($status)=($result =~ /%(\S+)/);
    return(1) if (!defined($status));
    return($status) if ($flag == 0);
    # otherwise check the flag & return the result.
    return($status & $flag);
}

sub timestr {
    my $td=DateTime->now();
    my $str=sprintf("%02d%02d%02d%02d%02d%02d",($td->year()%100,$td->month(),
						$td->day(),$td->hour(),$td->minute(),$td->second()));
    return($str);
}

sub set_aero_register {
    my ($posn,$sel,$fh,$rix,$val)=@_;
    $posn->{"dlog"}($sel,$fh,$posn->{"prepend"},
		    posnquot(sprintf("DGLOBAL(%d)=%g",$rix,$val)));
}

sub get_aero_register {
    my ($posn,$sel,$fh,$rix)=@_;
    $posn->{"dlog"}($sel,$fh,$posn->{"prepend"},
		    posnquot(sprintf("DGLOBAL(%d)",$rix)));
}

sub adjust_aero_stages {
    my ($adj_instruct)=@_;
    my $instr=$adj_instruct->{"instr"};
    my $adj_axis=$adj_instruct->{"AXIS"};
    my $delta=$adj_instruct->{"DELTA"};
    
}

sub ts5_pulsescan {
    # populate Aerotech register variables with appropriate parameters
    # required parameters
    my ($scan_instructions)=@_;
    my $instr      = $scan_instructions->{"instr"};
    my $positions=[$scan_instructions->{"from_pos"},
		   $scan_instructions->{"to_pos"}];
    my $scan_nsamp = $scan_instructions->{"nsamp"};
    my $dutycycle  = $scan_instructions->{"dutycycle"};
    # optional parameters
    my $slewspeed=100;
    if (defined($scan_instructions->{"slewspeed"})) {
	$slewspeed = $scan_instructions->{"slewspeed"}; 
    }
    # this ramprate is parasitically used by pulse_scan.bcx
    # as a proxy for a maximum acceleration which is in turn used
    # to set the ramp distance - distance over which to achieve
    # constant velocity. If too low, the ramp distance may be 
    # too large and travel limits may be exceeded..
    my $ramprate;
    $ramprate=$pulsescan_ramprate;
#    $ramprate=50.0;
    if (defined($scan_instructions->{"ramprate"})) {
	$ramprate  = $scan_instructions->{"ramprate"};
    }
    my $scurve=15;
    if (defined($scan_instructions->{"scurve"})) {
	$scurve  = $scan_instructions->{"scurve"};
    }

    my $posn=$instr->{"posn"};
    my $meas=$instr->{"meas"};
    my ($rix,$val);
    my $pwidth=0.010;
    my $register_targets={
	# sampling time
	"100" => $dwelltime,
	# starting & ending coordinates of scan
	"101" => $positions->[0]->[0],
	"102" => $positions->[0]->[1],
	"103" => $positions->[1]->[0],
	"104" => $positions->[1]->[1],
	# nsamples, duty cycle, slew speed, ramp rate, scurve & pulse time
	"105" => $scan_nsamp,
	"106" => $dutycycle,
	"107" => $slewspeed,
	"108" => $ramprate,
	"109" => $scurve,
	"110" => $pwidth};
    foreach my $addr ( sort keys %{$register_targets} ) {
	set_aero_register($posn,$sel,$fh,$addr,$register_targets->{$addr});
    }
  perform_pulsescan:
    # initialize keyence acquisition
    $meas->{"dlog"}($sel,$fh,$meas->{"prepend"},"AQ");
    # start keyence data acquisition
    $meas->{"dlog"}($sel,$fh,$meas->{"prepend"},"AS");
    # call coord_slew.bcx
    $posn->{"dlog"}($sel,$fh,$posn->{"prepend"},exequot("pulse_scan.bcx"));
    # wait until finished moving
    # read number of samples read
    my ($n1,$n2);
    my $t=[-1]; # for timestamps

    do {
	my $ret=$meas->{"dlog"}($sel,$fh,$meas->{"prepend"},"AN");
	($n1,$n2)=(split(',',$ret))[2,3];
	if (defined($n1)) {
	    printf STDERR "\tgot %d/%d\r",$n1,$scan_nsamp
		if ($verbose);
	} else {
	    printf STDERR "ret = $ret\n"
		if ($verbose);
	    $n1=1;
	} 
#	select(undef,undef,undef,$dwelltime/$dutycycle);
	# the following will reduce the number of ACTION commands
	# being sent to the CCS system..
	my $waittime=0.2;
	if (looks_like_number($n1)) {
	    $waittime=(($scan_nsamp-$n1)*$dwelltime/$dutycycle)/1.5;
	    $waittime=0.2 if ($waittime<0.2);
	}
	select(undef,undef,undef,$waittime); # while counting only interrogate @1Hz

	# capture approximate time of first data latch
	if (($t->[0]==-1) && ($n1>0)) {
	    $t->[0]=tv_interval($starttime,[gettimeofday()]);
	}
    } while ($n1<$scan_nsamp);

    # capture time of final data latch
    $t->[1]=tv_interval($starttime,[gettimeofday()]);

    # stop acquisition
    $meas->{"dlog"}($sel,$fh,$meas->{"prepend"},"AP");
    # read out the values
    my @z1=split(',',$meas->{"dlog"}($sel,$fh,$meas->{"prepend"},"AO,01"));
    my @z2=split(',',$meas->{"dlog"}($sel,$fh,$meas->{"prepend"},"AO,02"));
    if (($#z1-$[+1<$scan_nsamp)||($#z2-$[+1<$scan_nsamp)) {
	# unsuccessful scan. something is out of whack. report to screen.
	printf STDERR "scan is out of whack. returned keyence read arrays:\n"
	    if ($verbose);
	printf STDERR "z1: %s\n",join(' ',@z1)
	    if ($verbose);
	printf STDERR "z2: %s\n",join(' ',@z2)
	    if ($verbose);
	goto perform_pulsescan;
    }
    @z1=@z1[1..$scan_nsamp];
    @z2=@z2[1..$scan_nsamp];

    
    my @xlist=();
    my @ylist=();
    my $timestamps=[];
    my $retval;

    my $use_aero_coordinates=0;

    my $aval=1.0/($scan_nsamp*(1+(1-1.0/$scan_nsamp)*(1.0/$dutycycle-1)));
    my $bval=$aval*(1.0/$dutycycle-1);
    my $aplusb = floor(($aval+$bval)*2000+0.5)/2000.0;

    foreach my $ix (0..$#z1) {
	my $scale = $ix*$aplusb + 0.5*$aval;
	push(@{$timestamps},sprintf("%.4f",$t->[0]+$scale*($t->[1]-$t->[0])));
    }

    if ($use_aero_coordinates) {
	my $doffset=150;
	
	foreach my $ix (0..$#z1) {
	    my $r1=get_aero_register($posn,$sel,$fh,$doffset+2*$ix+0);
	    my $r2=get_aero_register($posn,$sel,$fh,$doffset+2*$ix+1);
	    push(@xlist,$r1 =~ /%(\S+)/);
	    push(@ylist,$r2 =~ /%(\S+)/);
	}
    } else {
	# compute the positions based on $positions, $scan_nsamp & $dutycycle
	my $poslist=[[],[]];
	my $dx=[$positions->[1]->[0]-$positions->[0]->[0],
		$positions->[1]->[1]-$positions->[0]->[1]];
	foreach my $ix (0..$#z1) {
	    my $scale = $ix*$aplusb + 0.5*$aval;
	    push(@{$poslist->[0]},
		 sprintf("%8.4f",$positions->[0]->[0]+$scale*$dx->[0]));
	    push(@{$poslist->[1]},
		 sprintf("%8.4f",$positions->[0]->[1]+$scale*$dx->[1]));
	}

	$retval={"prog_x"   => $poslist->[0],
		 "prog_y"   => $poslist->[1],
		 "key_z1"   => [@z1],
		 "key_z2"   => [@z2],
		 "timestamp"=> $timestamps};
    }

    my $headings=["prog_x","prog_y","key_z1","key_z2","timestamp"];

    if ($use_aero_coordinates) {
	$retval->{"aero_x"} = [@xlist];
	$retval->{"aero_y"} = [@ylist];
	$headings=["aero_x","aero_y",
		   "prog_x","prog_y",
		   "key_z1","key_z2",
		   "timestamp"];
    }

    # read in the aerotech captured positions after move is complete
    do {} while(planestatus($posn,1,0.15));
    return($headings,$retval);
}

sub flush_read_buffers {
    my ($sel)=@_;
    my $answer;
    my $ret=0;
    my @fhs=$sel->{"ANY"}->can_read(0);
    foreach my $fh (@fhs) {
	if (0) {
	    $answer=readline($fh);
	} else {
	    sysread($fh,$answer,409600);
	}

	{
	    printf FLU "%d ---\n",$nflu;
	    printf FLU "%s",$answer;
	    $nflu++;
	}
	
	printf STDERR "read orphaned text on fh $fh: $answer\n"
	    if ($verbose);
	$ret=1;
    }
    $ret;
}

