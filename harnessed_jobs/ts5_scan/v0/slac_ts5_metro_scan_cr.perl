#!/usr/bin/perl
use strict;
use warnings;
use POSIX;
use Getopt::Long;

my $raft_os=[9.01,-19.105]; # millimeters
$raft_os=[-42,37.5];
my $raft_theta=0.173;    # degrees (checked against sense of stage x,y)
$raft_theta=-90;
my ($include_sensors,$include_reref,$include_fiducials,$include_selfcal)=(1,1,1,0);
my ($sensor_step_sample,$fiducial_step_sample)=(0,0);
my $reref_cen=[[-55,-15-42.5],[0,+15+42.5],[55,-15-42.5]];
$reref_cen=[[0,45],[30,75],[75,0]];
my $sensor_dim=[40.5,40.5];
my $gs_sensor_dim=$sensor_dim;
my $wfs_sensor_dim=[41.0,20.0];
my $selfcal={"sensor" => [[0,-20],[0,20]],
	     "fid"    => [[0,-33],[0,33]],
		 "spacing"=> 0.5};
# corner raft case
$selfcal->{"fid"}=[[-12,0],[12,0]];
$selfcal->{"sensor"}=[[-19,0],[19,0]];

my $usage="USAGE:\t$0 [args] [> <plan_file>]\n".
    "\nif the environment variable LCATR_TS5_OPTS is defined, the file that\n".
    "\tthis points to will be scanned for options usable by $0 and all\n".
    "\t[args] will throw an error.\n".
    "\n[args] are any combination of:\n".
    "\t[--sensor_sample_spacing=<spacing[mm/sample]>]\n".
    "\t[--fiducial_sample_spacing=<spacing[mm/sample]>]\n".
    "\t[--sensor_step_sample] #(park-measure-move, off by default)\n".
    "\t[--fiducial_step_sample] #(park-measure-move, off by default)\n".
    "\t[--samples_between_reref=<samples_betw_refeferenc>]\n".
    "\t[--raft_center_x=<aero_x[mm]>]\n".
    "\t[--raft_center_y=<aero_y[mm]>]\t#(placeholder coordinates will be\n".
    "\t\t\t\t\t  reset if either raft_center\n".
    "\t\t\t\t\t  coordinates are specified)\n".
    "\t[--raft_theta=<theta[deg]>  #(raft center r.h. rotation about -Z)\n".
    "\t\t  Note: Aerotech XYZ stack form a left handed coordinate\n".
    "\t\t  system. Higher/proud (positive) image heights interpreted\n".
    "\t\t  as the Z coordinate would be part of a right handed system\n".
    "\t\t  that share aero_x & aero_y (but not aero_z).\n".
    "\t[--exclude_sensors] [--exclude_rereferences] [--exclude_fiducials]\n".
    "\t[--only_sensors=<include_sensors>]\n".
    "\t\t#(colon delimited list, e.g. S00:S10:S20 for bottom row sensors)\n".
    "\t[--reref=reref0_x:reref0_y][--reref=reref1_x:reref1_y].. (raft_x,raft_y)\n".
    "\t[--report_corners] #(report corners of raft for alignment)\n".
    "\t[--selfcal dz0:dz1:dz2:dz3:..:dzN ] #(acquire defined selfcal scans on specified dz list)\n".
    "\t[--help]\n";

# >>> TS5_METRO_SCAN_FIDUCIAL_SAMPLE_SPACING  	0.5                 
# >>> TS5_METRO_SCAN_PLAN                     	~/scanplan_170918.sp
# >>> TS5_METRO_SCAN_RAFT_CENTER_X            	9.2                 
# >>> TS5_METRO_SCAN_RAFT_CENTER_Y            	-15                 
# >>> TS5_METRO_SCAN_RAFT_THETA               	0.173               
# >>> TS5_METRO_SCAN_REPORT_CORNERS           	TRUE                
# >>> TS5_METRO_SCAN_SAMPLES_BETWEEN_REREF    	200                 
# >>> TS5_METRO_SCAN_SELFCAL                  	-0.5:-0.25:0:0.25:0.5
# >>> TS5_METRO_SCAN_SENSOR_SAMPLE_SPACING    	0.5                 

my ($raft_center_x,$raft_center_y,$raft_rotation,
    $exclude_sensors,$exclude_reref,$exclude_fiducials,
    $these_sensors,$report_corners,
    $fiducial_sample_spacing,$sensor_sample_spacing,
    $samples_betw_reref,$selfcal_dz_list,$metro_scan_plan_file);

($fiducial_sample_spacing,$sensor_sample_spacing)=(1,1);
$samples_betw_reref=160;
my @reref_coords;
my $rerefcoords;
my @do_sensors;
my $help=0;

my $opts=$ENV{join("_","LCATR","TS5_OPTS")};
if (! defined($opts)) {
    GetOptions("raft_center_x=s" => \$raft_center_x,
	       "raft_center_y=s" => \$raft_center_y,
	       "raft_theta=s"    => \$raft_rotation,
	       "sensor_sample_spacing=s" => \$sensor_sample_spacing,
	       "fiducial_sample_spacing=s" => \$fiducial_sample_spacing,
	       "samples_between_reref=i" => \$samples_betw_reref,
	       "exclude_sensors" => \$exclude_sensors,
	       "exclude_reref"   => \$exclude_reref,
	       "exclude_fiducials" => \$exclude_fiducials,
	       "sensor_step_sample" => \$sensor_step_sample,
	       "fiducial_step_sample" => \$fiducial_step_sample,
	       "only_sensors=s"  => \$these_sensors,
	       "reref=s"         => \@reref_coords,
	       "report_corners"  => \$report_corners,
	       "selfcal_dz_list=s"  => \$selfcal_dz_list,
	       "help"            => \$help) ||
	die("Error in command line arguments! exiting..\n".$usage);
    if (@ARGV) {
	printf STDERR "left over command line entries: %s\n",join(' ',@ARGV);
	die($usage);
    }
} else {
    printf STDERR "opts is defined as %s\n",$opts;
    if ($#ARGV>-1) {
	printf STDERR ("command line arguments will be ignored: %s\n",
		       join(' ',@ARGV));
	printf STDERR ("re-run $0 without arguments or unset environment ".
		       "variable %s.\nexiting..\n",
		       join("_","LCATR","TS5_OPTS"));
	exit(1);
    }
    my $pars=retrieve_opts($opts);
    my %par_hash=(
	"TS5_METRO_SCAN_FIDUCIAL_SAMPLE_SPACING"=> \$fiducial_sample_spacing,
	"TS5_METRO_SCAN_PLAN"                   => \$metro_scan_plan_file,
	"TS5_METRO_SCAN_RAFT_CENTER_X"          => \$raft_center_x,
	"TS5_METRO_SCAN_RAFT_CENTER_Y"          => \$raft_center_y,
	"TS5_METRO_SCAN_RAFT_THETA"             => \$raft_rotation,
	"TS5_METRO_SCAN_REPORT_CORNERS"         => \$report_corners,
	"TS5_METRO_SCAN_SAMPLES_BETWEEN_REREF"  => \$samples_betw_reref,
	"TS5_METRO_SCAN_SELFCAL"                => \$selfcal_dz_list,
	"TS5_METRO_SCAN_SENSOR_SAMPLE_SPACING"  => \$sensor_sample_spacing);

    foreach my $key (keys %{$pars}) {
	if (defined($par_hash{$key})) {
	    ${$par_hash{$key}} = $pars->{$key};
	} else {
	    # no corresponding $par_hash{$key}. probably for another TS5 program. skipping..
	}
    }
    $report_corners = uc $report_corners;
    undef $report_corners if (($report_corners eq "FALSE") || ($report_corners eq 0));
}

if ($help) {
    die($usage);
}

$selfcal->{"dz_list"}=[split(':',$selfcal_dz_list)];

$raft_theta=$raft_rotation if (defined($raft_rotation));
if (defined($raft_center_x) || defined($raft_center_y)) {
    $raft_os=[0,0];
    $raft_os->[0]=$raft_center_x if (defined($raft_center_x));
    $raft_os->[1]=$raft_center_y if (defined($raft_center_y));
}

if (defined($these_sensors)) {
    my %sens=();
    foreach my $ds (split(':',$these_sensors)) {
	if ($ds !~ /S[0-2][0-2]/) {
	    printf STDERR "invalid sensor name $ds. should be one of:\n";
	    printf STDERR "\t\tS00,S01,S02\n";
	    printf STDERR "\t\tS10,S11,S22\n";
	    printf STDERR "\t\tS20,S21,S22\n";
	    print STDERR $usage;
	    exit;
	}
	$sens{$ds}=1;
    }
    @do_sensors=sort keys %sens;
}

$exclude_sensors=1   if (@do_sensors);
$include_sensors=0   if (defined($exclude_sensors));
$include_reref=0     if (defined($exclude_reref));
$include_fiducials=0 if (defined($exclude_fiducials));
$include_selfcal=1   if (defined($selfcal->{"dz_list"}));

if (@reref_coords) {
    foreach my $rrc (@reref_coords) {
	push(@{$rerefcoords},[split(':',$rrc)]);
    }
    # replace the nominal list of rererference coords
    # these are in raft coordinates.
    $reref_cen=$rerefcoords;
}

# print (STDERR) run parameters to the screen
my $str;
$str=sprintf("$0 will run with the following\n".
	     "parameters:\n");
$str .= sprintf("report corners=1\n") if (defined($report_corners));
$str .= sprintf("{sensor,fiducial}_sample_spacing=(%g,%g)\n",
		$sensor_sample_spacing,$fiducial_sample_spacing);
$str .= sprintf("{sensor,fiducial}_step_sample=(%d,%d)\n",
		$sensor_step_sample,$fiducial_step_sample);
$str .= sprintf("sampes_per_reref  =  %g\n",$samples_betw_reref),
$str .= sprintf("raft_center_(x,y) = (%g,%g)\n",@{$raft_os});
$str .= sprintf("raft_theta        =  %g\n",$raft_theta);
$str .= sprintf("will scan only sensors: %s\n",join(',',@do_sensors))
		if (@do_sensors);
$str .= sprintf("exclude_(sensors,reref,fiducials) = (%d,%d,%d)\n",
		($include_sensors)?0:1,
		($include_reref)?0:1,
		($include_fiducials)?0:1);

if (@{$reref_cen}) {
    $str .= sprintf("will use rereference coordinates (raft cooordinate system):\n");
    foreach my $rrc (@{$reref_cen}) {
	$str .= sprintf("\t(%f,%f)\n",@{$rrc});
    }
}

$str .= sprintf("will scan this set of sensors: %s\n",join(',',@do_sensors));
if (defined($selfcal->{"dz_list"})) {
    $str .= sprintf("will self calibrate for the following list of dz values: (%s)\n",
		    join(',',split(':',$selfcal->{"dz_list"})));
    $str .= sprintf("\tfor sensors (local coords) (%s,%s)->(%s,%s) in steps of %s\n",
		    @{$selfcal->{"sensor"}->[0]},@{$selfcal->{"sensor"}->[1]},
		    $selfcal->{"spacing"});
    $str .= sprintf("\tfor fiducials (local coords) (%s,%s)->(%s,%s) in steps of %s\n",
		    @{$selfcal->{"fid"}->[0]},@{$selfcal->{"fid"}->[1]},
		    $selfcal->{"spacing"});
}

print STDERR $str;

if (($include_fiducials==0) && ($include_selfcal==0) &&
    (($include_sensors==0) && (! @do_sensors))) {
    printf STDERR "wait .. nothing to measure, what's the point of rereferencing??\nexiting..\n";
    exit(1);
}

# specify the output file..
my $SPF;
if (defined($metro_scan_plan_file)) {
    open($SPF,">",$metro_scan_plan_file) || die "can't open $metro_scan_plan_file. exiting..\n";
} else {
    $SPF=*STDOUT;
}

##################################################################
# PROCEED WITH SCAN PLAN GENERATION
##################################################################

printf $SPF "! TF X0=%f\n",$raft_os->[0];
printf $SPF "! TF Y0=%f\n",$raft_os->[1];
printf $SPF "! TF theta=%f\n",$raft_theta;

my $ss=get_scanspecs();

if (defined($report_corners)) {
    # go through the label and report. Then exit.
    my %n_by_label=("fid0" => 2,"fid1" => 2,
		    "S00"  => 1,"S02"  => 1,"S20"  => 1,"S22"  => 1,
		    "S01"  => 0,"S21"  => 0,"S10"  => 0,"S12"  => 0,"S11"  => 0,
		    "REREF"=> 0,
		    "SELFCAL_S00" => 0, "SELFCAL_S01" => 0, "SELFCAL_S02" => 0,
		    "SELFCAL_S10" => 0, "SELFCAL_S11" => 0, "SELFCAL_S12" => 0,
		    "SELFCAL_S20" => 0, "SELFCAL_S21" => 0, "SELFCAL_S22" => 0,
		    "SELFCAL_fid0"=> 0, "SELFCAL_fid1"=> 0
	);
    
    foreach my $ssv (@{$ss}) {
	foreach my $ix0 (0..$#{$ssv}) {
	    my $ptlist=[];
	    my ($xc,$yc)=@{$ssv->[$ix0]->{"cen"}};
	    my ($xoff,$yoff)=@{$ssv->[$ix0]->{"lat_offset"}};
	    foreach my $x (@{$ssv->[$ix0]->{"x"}}) {
		foreach my $y (@{$ssv->[$ix0]->{"y"}}) {
		    my ($xv,$yv)=($x+$xoff+$xc,$y+$yoff+$yc);
		    push(@{$ptlist},[$xv,$yv]);
		}
	    }
	    # pick the largest radius from $ptlist
	    my @sorted_ptlist=reverse sort {pow($ptlist->[$a]->[0],2)+pow($ptlist->[$a]->[1],2) <=>
						pow($ptlist->[$b]->[0],2)+pow($ptlist->[$b]->[1],2)} (0..$#{$ptlist});

	    if ($n_by_label{$ssv->[$ix0]->{"label"}}>0) {
		if ($ssv->[$ix0]->{"label"} =~ /S/) {
		    printf STDERR ("extrema for label %s (spot near corner of sensor should should be %.2f mm from either edge):\n",
				   $ssv->[$ix0]->{"label"},
				   abs((42.25-($sensor_dim->[0]+$sensor_dim->[1])/2.0)/2.0)) ;
		} else {
		    printf STDERR ("extrema for label %s:\n",$ssv->[$ix0]->{"label"}) ;
		}
	    }

	    for (my $report_ix=0;$report_ix<$n_by_label{$ssv->[$ix0]->{"label"}};$report_ix++) {
		my $radial_extreme=$ptlist->[$sorted_ptlist[$report_ix]];
		# now transform into motor coordinates.
		my $tf_coords;
		{
		    my $theta=$raft_theta;
		    my $offset=$raft_os;
		    my $deg=atan2(1,1)/45.0;
		    my ($sn,$cs)=(sin($raft_theta*$deg),cos($raft_theta*$deg));
		    $tf_coords=[$cs*$radial_extreme->[0]-$sn*$radial_extreme->[1]+$offset->[0],
				$sn*$radial_extreme->[0]+$cs*$radial_extreme->[1]+$offset->[1]];
		}
		printf STDERR ("%s\n",
			       sprintf("metrology/Positioner aerotechChat \"\'MOVEABS X %f XF %g Y %f YF %g\'\"",
				       $tf_coords->[0],50,$tf_coords->[1],50));
	    }
	}
    }
    # finally print out instructions to move to raft center
    printf STDERR ("RAFT CENTER:\n");
    printf STDERR ("%s\n",
		   sprintf("metrology/Positioner aerotechChat \"\'MOVEABS X %f XF %g Y %f YF %g\'\"",
			   $raft_os->[0],50,$raft_os->[1],50));
    exit(1);
#    exit;
}

my $scl=[];
my $lbl=[];
my $reref=[];
my $selfc=[];
my $selfc_lbl=[];

foreach my $ssv (@{$ss}) { # loop over scan types - but skip over SELFCAL - those should come at the end
    foreach my $ix0 (sort keys @{$ssv}) { # loop over unique labels
	if (! $include_fiducials) {
	    next if ($ssv->[$ix0]->{"label"} =~ /^fid/);
	}

	if ((! $include_sensors) && 
	    (($ssv->[$ix0]->{"label"} =~ /^S\d\d/) ||
	     ($ssv->[$ix0]->{"label"} =~ /^GS\d/) ||
	     ($ssv->[$ix0]->{"label"} =~ /^WFS\d/))) {
	    printf STDERR "label gotten is %s\n",$ssv->[$ix0]->{"label"};
	    # and look for a match in @do_sensors (if defined)
	    if (@do_sensors) {
		my $match_found=0;
		foreach my $ds (@do_sensors) {
		    $match_found=1 if ($ssv->[$ix0]->{"label"} =~ /^$ds/);
		}
		next if (!$match_found);
	    } else {
		next if ($ssv->[$ix0]->{"label"} =~ /^S\d\d/);
	    }
	}

#	printf STDERR "label gotten is %s (ix0 is $ix0)\n",$ssv->[$ix0]->{"label"};
#	printf STDERR "hash is: %s\n",join(' ',%{$ssv->[$ix0]});

	my $scan_lists=expand_scan($ssv->[$ix0],$raft_os,$raft_theta);
	# special scans (reref & selfcal)
	if ($ssv->[$ix0]->{"label"} =~ /REREF/) {
	    # divert the rereference to a different list
	    push(@{$reref},$scan_lists);
	    printf STDERR "REREF label: %s\n",$ssv->[$ix0]{"label"};
	    next;
	}
	if ($ssv->[$ix0]->{"label"} =~ /SELFCAL/) {
	    # divert the rereference to a different list
	    push(@{$selfc},$scan_lists);
	    push(@{$selfc_lbl},$ssv->[$ix0]->{"label"});
	    printf STDERR "SELFCAL label: %s\n",$ssv->[$ix0]{"label"};
	    next;
	}

	push(@{$scl},$scan_lists);
	# should make more lists here for use later on (labels, etc.)
	push(@{$lbl},$ssv->[$ix0]{"label"});
	printf STDERR "label: %s\n",$ssv->[$ix0]{"label"};
    }
}

# @scl now includes a list of lists, which now contain the coordinates of the sampling
# positions.

# make up a list of possible starting points and directions indexed by $scan_ix
# which in turn references $scan_id.

my $scan_ix=0;
my $full_scan_list=[];
my $reref_scan_list=[];
my $selfc_scan_list=[];

foreach my $obj_scan_ix (0..$#{$scl}) {
    foreach my $scan_trace_ix (0..$#{$scl->[$obj_scan_ix]}) {
	my @coord_pair_list=@{$scl->[$obj_scan_ix]->[$scan_trace_ix]};
	my @ends=@coord_pair_list[0,$#coord_pair_list];
	$full_scan_list->[$scan_ix]={};
	$full_scan_list->[$scan_ix]->{"scoord"}=$ends[0];
	$full_scan_list->[$scan_ix]->{"direction"}=+1;
	$full_scan_list->[$scan_ix]->{"label"}=$lbl->[$obj_scan_ix];
	$full_scan_list->[$scan_ix]->{"scan"}=$scl->[$obj_scan_ix]->[$scan_trace_ix];
	$scan_ix++;
	$full_scan_list->[$scan_ix]={};
	$full_scan_list->[$scan_ix]->{"scoord"}=$ends[1];
	$full_scan_list->[$scan_ix]->{"direction"}=-1;
	$full_scan_list->[$scan_ix]->{"label"}=$lbl->[$obj_scan_ix];
	$full_scan_list->[$scan_ix]->{"scan"}=$scl->[$obj_scan_ix]->[$scan_trace_ix];
	$scan_ix++;
    }
}

# do something similar for rereferencing
$scan_ix=0;
foreach my $reref_scan_ix (0..$#{$reref}) {
    foreach my $reref_trace_ix (0..$#{$reref->[$reref_scan_ix]}) {
	my @coord_pair_list=@{$reref->[$reref_scan_ix]->[$reref_trace_ix]};
	my @ends=@coord_pair_list[0,$#coord_pair_list];
	$reref_scan_list->[$scan_ix]={};
	$reref_scan_list->[$scan_ix]->{"scoord"}=$ends[0];
	$reref_scan_list->[$scan_ix]->{"direction"}=+1;
	$reref_scan_list->[$scan_ix]->{"label"}=$lbl->[$reref_scan_ix];
	$reref_scan_list->[$scan_ix]->{"scan"}=$reref->[$reref_scan_ix]->[$reref_trace_ix];
	$scan_ix++;
    }
}
# and now $reref_scan_list is populated.

# do something similar for selfcal
$scan_ix=0;
foreach my $selfc_scan_ix (0..$#{$selfc}) {
    foreach my $selfc_trace_ix (0..$#{$selfc->[$selfc_scan_ix]}) {
	my @coord_pair_list=@{$selfc->[$selfc_scan_ix]->[$selfc_trace_ix]};
	my @ends=@coord_pair_list[0,$#coord_pair_list];
	$selfc_scan_list->[$scan_ix]={};
	$selfc_scan_list->[$scan_ix]->{"scoord"}=$ends[0];
	$selfc_scan_list->[$scan_ix]->{"direction"}=+1;
	$selfc_scan_list->[$scan_ix]->{"label"}=$selfc_lbl->[$selfc_scan_ix];
	$selfc_scan_list->[$scan_ix]->{"scan"}=$selfc->[$selfc_scan_ix]->[$selfc_trace_ix];
	$scan_ix++;
    }
}
# and now $sefc_scan_list is populated.

my $next_scan_ix=0;
my ($start,$stop);
my $total_scan_distance=0;
my $step_number=0;
my $prev_coords;
my $n_scan_samples=0;


if (!(($include_fiducials==0) && (($include_sensors==0) && (! @do_sensors)))) {
    if ($include_reref) {
	printf $SPF "%s",sample_reference($reref_scan_list);
    }
    do {
	# output scan using next_scan_ix and record the scan array for identifying later.
	my $target_scan=$full_scan_list->[$next_scan_ix]->{"scan"};
	# print out the scan as appropriate, ignore label for now
	my @scanlist=@{$full_scan_list->[$next_scan_ix]->{"scan"}};
	@scanlist=reverse @scanlist if ($full_scan_list->[$next_scan_ix]->{"direction"}==-1);
	my $stop=$scanlist[$#scanlist];
	$total_scan_distance += sqrt(pow($scanlist[0]->[0]-$stop->[0],2)+
				     pow($scanlist[0]->[1]-$stop->[1],2));

	my $lbl=$full_scan_list->[$next_scan_ix]->{"label"};
	printf $SPF "! part of label %s\n",$lbl;
	my $do_step=0;
	$do_step=1 if ((($lbl =~ /^S\d\d/) &&   ($sensor_step_sample==1))|| 
		       (($lbl =~ /^fid\d/) && ($fiducial_step_sample==1)));

	if (! $do_step) {
	    # prepares scan delimeters
	    printf $SPF "! SCAN n=%d dc=%f\n",$#scanlist-$[+1,0.95;
	    foreach my $i (0,$#scanlist) {
		printf $SPF "%g %g\n",@{$scanlist[$i]};
	    }
	    $n_scan_samples += ($#scanlist-$[+1);
	} else { # prepares a visit list
	    foreach my $i (0..$#scanlist) {
		printf $SPF "%g %g\n",@{$scanlist[$i]};
		$n_scan_samples++;
	    }
	}

	# and remove elements that contain this scan.
	my $i=0;
	do {
	    if ($target_scan eq $full_scan_list->[$i]->{"scan"}) {
		splice(@{$full_scan_list},$i,1);
		$i--;
	    }
	    $i++;
	} until ($i>$#{$full_scan_list});
	# identify the next starting point based on separation
	my @scan_ixlist_by_distance;
	@scan_ixlist_by_distance=
	    sort {(pow($full_scan_list->[$a]->{"scoord"}->[0]-$stop->[0],2)+
		   pow($full_scan_list->[$a]->{"scoord"}->[1]-$stop->[1],2)) <=>
		   (pow($full_scan_list->[$b]->{"scoord"}->[0]-$stop->[0],2)+
		    pow($full_scan_list->[$b]->{"scoord"}->[1]-$stop->[1],2))}
	(0..$#{$full_scan_list});

	# @scan_ixlist_by_distance = reverse @scan_ixlist_by_distance;

	# every 10 scans pick a number out of a hat to resume with a randomly chose location
	my $lookup_index=0;
#    if ( ($step_number+1) % $scans_per_patch == 0) {
	if ( ($n_scan_samples) / $samples_betw_reref >= 1) {
	    $n_scan_samples=0; # to reset the condition
	    # rereference, if applicable
	    if ($include_reref) {
		printf $SPF "%s",sample_reference($reref_scan_list);
	    }
	    $lookup_index = rand($#{$full_scan_list});
	}
	
	$next_scan_ix=$scan_ixlist_by_distance[$lookup_index];

	if (defined($next_scan_ix)) {
	    $total_scan_distance += 
		sqrt(pow($full_scan_list->[$next_scan_ix]->{"scoord"}->[0]-$stop->[0],2)+
		     pow($full_scan_list->[$next_scan_ix]->{"scoord"}->[1]-$stop->[1],2));
	}
	$step_number++;
    } until ($#{$full_scan_list}<0);
    if ($include_reref) {
	printf $SPF "%s",sample_reference($reref_scan_list);
    }
}

# do the selfcal here.
if ($include_selfcal==1) {
    foreach my $delta_z (@{$selfcal->{"dz_list"}}) {
	printf $SPF "! ADJUST Z %f\n",$delta_z;
	printf $SPF "! WAIT %f\n",5;
	if ($include_reref) {
	    printf $SPF "%s",sample_reference($reref_scan_list);
	}
	printf $SPF "%s",sample_selfcal($selfc_scan_list);
	if ($include_reref) {
	    printf $SPF "%s",sample_reference($reref_scan_list);
	}
	printf $SPF "! ADJUST Z %f\n",-1*$delta_z; # set things back
	printf $SPF "! WAIT %f\n",5;
    }
}

printf STDERR "total scan distance: %g\n",$total_scan_distance;

exit;

sub expand_scan {
    my ($sc,$offset,$theta)=@_;
    my ($x,$y);

    my $grid_1d={};
    foreach my $ax ("x","y") {
	$grid_1d->{$ax}=[];
	for (my $ix=0;$ix<$sc->{"n".$ax};$ix++) {
	    push(@{$grid_1d->{$ax}},$sc->{$ax}->[0]+
	     ($sc->{$ax}->[1]-$sc->{$ax}->[0])*$ix/
	     ($sc->{"n".$ax}-1.0-1e-8));
	}
    }

    my ($outer_loop,$inner_loop)=("x","y");
    ($outer_loop,$inner_loop)=("y","x") if ($sc->{"outer_loop_y"});
    my @results=();
    my $coord={};
    my $deg=atan2(1,1)/45.0;
    my ($cs,$sn)=(cos($sc->{"rot"}*$deg),sin($sc->{"rot"}*$deg));
    my ($cstheta,$sntheta)=(cos($theta*$deg),sin($theta*$deg));
    
    foreach my $ol_ix (0..$#{$grid_1d->{$outer_loop}}) {
	$coord->{$outer_loop} = $grid_1d->{$outer_loop}->[$ol_ix];
	my @il=();
	@il=(0..$#{$grid_1d->{$inner_loop}});
#	@il = reverse @il if ($ol_ix%2==1); # don't reverse for now, optimization/randomization will occur above.
	my @res=();
	foreach my $il_ix (@il) {
	    $coord->{$inner_loop}=$grid_1d->{$inner_loop}->[$il_ix];
	    my $xy=[$cs*$coord->{"x"}-$sn*$coord->{"y"},
		    $sn*$coord->{"x"}+$cs*$coord->{"y"}];
	    foreach my $i (0,1) {
		$xy->[$i] += ($sc->{"cen"}->[$i]+$sc->{"lat_offset"}->[$i]);
	    }
	    push(@res,[($cstheta*$xy->[0]-$sntheta*$xy->[1]) + $offset->[0],
		       ($sntheta*$xy->[0]+$cstheta*$xy->[1]) + $offset->[1]]);
	}
	push(@results,[@res]);
    }
    return([@results]);
}

sub get_scanspecs {
    my $fid_dim=[11.7,74];
    # corner raft case
    $fid_dim=[22.5,19];
    my $samp=[1,1];
    $samp=[$fiducial_sample_spacing,
	   $fiducial_sample_spacing];
    my $fid_cen;
    my $fid_rot=0;
    my $raft_cen=[30,-40];
    $raft_cen=[0,0];
    my $fid_x_offset=(190-12.7)/2.0;
    my $lat_offset={};
    my $ip_rot={};
    my $gs_ip_rot={};
    my $wfs_ip_rot={};
    my $gs_lat_offset={};
    my $wfs_lat_offset={};

    foreach my $sen_i ( 0..2 ) {
	foreach my $sen_j ( 0..2 ) {
	    $lat_offset->{$sen_i,$sen_j}=[$sen_j-1,$sen_i-1]; # seems to work..
	    $ip_rot->{$sen_i,$sen_j}=1.5*($sen_i+$sen_j); 
	    # zero lateral offsets & in-plane rotations
	    # remove before flight?
	    $lat_offset->{$sen_i,$sen_j}=[0,0];
	    $ip_rot->{$sen_i,$sen_j}=0;
	}
    }
    foreach my $gs_ix (0..1) {
	$gs_ip_rot->{$gs_ix}=0;
	$gs_lat_offset->{$gs_ix}=[0,0];
    }
    foreach my $wfs_ix (0..1) {
	$wfs_ip_rot->{$wfs_ix}=0;
	$wfs_lat_offset->{$wfs_ix}=[0,0];
    }

    my $scanspec_fiducial=[];
    my $selfcal_spec_fiducial=[];

    my $selfcal_dim=[abs($selfcal->{"fid"}->[0]->[0]-$selfcal->{"fid"}->[1]->[0]),
		     abs($selfcal->{"fid"}->[0]->[1]-$selfcal->{"fid"}->[1]->[1])];

    if (0) {
	# science raft case
	$fid_cen=[$raft_cen->[0]-$fid_x_offset,$raft_cen->[1]];
	$fid_rot=0;
    } else {
	# corner raft case
	$fid_cen=[$raft_cen->[0]+68.5+42.285+(0)*(-60/sqrt(2)),$raft_cen->[1]+68.5-0.1414+(0)*(+60/sqrt(2))];
	$fid_rot=45;
    }

    $scanspec_fiducial->[0]={"x" => [-$fid_dim->[0]/2.0,+$fid_dim->[0]/2.0],
				 "y" => [-$fid_dim->[1]/2.0,+$fid_dim->[1]/2.0],
				 "nx" => floor($fid_dim->[0]/$samp->[0]+1),
				 "ny" => floor($fid_dim->[1]/$samp->[1]+1),
				 "cen" => $fid_cen,
				 "rot"=> $fid_rot,
				 "lat_offset" => [0,0],
				 "outer_loop_y" => 0,
				 "label" => "fid0"};

    $selfcal_spec_fiducial->[0]={"x" => [$selfcal->{"fid"}->[0]->[0],$selfcal->{"fid"}->[1]->[0]],
				     "y" => [$selfcal->{"fid"}->[0]->[1],$selfcal->{"fid"}->[1]->[1]],
				     "nx" => floor($selfcal_dim->[0]/$selfcal->{"spacing"}+1),
				     "ny" => floor($selfcal_dim->[1]/$selfcal->{"spacing"}+1),
				     "cen" => $fid_cen,
				     "rot"=> $fid_rot,
				     "lat_offset" => [0,0],
				     "outer_loop_y" => 0,
				     "label" => "SELFCAL_fid0"};

    if (0) {
	# science raft case
	$fid_cen=[$raft_cen->[0]+$fid_x_offset,$raft_cen->[1]];
    } else {
	# corner raft case
	$fid_cen=[$raft_cen->[0]+68.5+42.285+(1)*(-60/sqrt(2)),$raft_cen->[1]+68.5-0.1414+(1)*(+60/sqrt(2))];
    }

    $scanspec_fiducial->[1]={"x" => [-$fid_dim->[0]/2.0,+$fid_dim->[0]/2.0],
				 "y" => [-$fid_dim->[1]/2.0,+$fid_dim->[1]/2.0],
				 "nx" => floor($fid_dim->[0]/$samp->[0]+1),
				 "ny" => floor($fid_dim->[1]/$samp->[1]+1),
				 "cen" => $fid_cen,
				 "rot"=> $fid_rot,
				 "lat_offset" => [0,0],
				 "outer_loop_y" => 1,
				 "label" => "fid1"};

    $selfcal_spec_fiducial->[1]={"x" => [$selfcal->{"fid"}->[0]->[0],$selfcal->{"fid"}->[1]->[0]],
				     "y" => [$selfcal->{"fid"}->[0]->[1],$selfcal->{"fid"}->[1]->[1]],
				     "nx" => floor($selfcal_dim->[0]/$selfcal->{"spacing"}+1),
				     "ny" => floor($selfcal_dim->[1]/$selfcal->{"spacing"}+1),
				     "cen" => $fid_cen,
				     "rot"=> $fid_rot,
				     "lat_offset" => [0,0],
				     "outer_loop_y" => 0,
				     "label" => "SELFCAL_fid1"};
    if (1) {
	# for corner raft..
	$selfcal_spec_fiducial->[0]->{"outer_loop_y"}=1;
	$selfcal_spec_fiducial->[1]->{"outer_loop_y"}=1;
    }

    # move onto sensors
    $samp=[1,1];
    $samp=[$sensor_sample_spacing,
	   $sensor_sample_spacing];
    my $sensor_cen;
    my $scanspec_sensors=[];
    my $selfcal_spec_sensors=[];

    $selfcal_dim=[abs($selfcal->{"sensor"}->[0]->[0]-$selfcal->{"sensor"}->[1]->[0]),
		  abs($selfcal->{"sensor"}->[0]->[1]-$selfcal->{"sensor"}->[1]->[1])];

    if (0) {
	# science raft case
	foreach my $sen_i ( 0..2 ) {
	    foreach my $sen_j ( 0..2 ) {
		$sensor_cen=[$raft_cen->[0]+($sen_i-1)*(-42.25),  # sign flip:
			     $raft_cen->[1]+($sen_j-1)*(+42.25)]; # CCS coordsys
		$scanspec_sensors->[3*$sen_j+$sen_i]={
		    "x" => [-$sensor_dim->[0]/2.0,+$sensor_dim->[0]/2.0],
			"y" => [-$sensor_dim->[1]/2.0,+$sensor_dim->[1]/2.0],
			"nx" => floor($sensor_dim->[0]/$samp->[0]+1),
			"ny" => floor($sensor_dim->[1]/$samp->[1]+1),
			"cen" => $sensor_cen,
			"rot"=> $ip_rot->{$sen_i,$sen_j},
			"outer_loop_y" => ($sen_i+$sen_j)%2,
			"lat_offset"   => $lat_offset->{$sen_i,$sen_j},
			"label"        => "S".$sen_i.$sen_j};
		$selfcal_spec_sensors->[3*$sen_j+$sen_i]={
		    "x" => [$selfcal->{"sensor"}->[0]->[0],$selfcal->{"sensor"}->[1]->[0]],
			"y" => [$selfcal->{"sensor"}->[0]->[1],$selfcal->{"sensor"}->[1]->[1]],
			"nx" => floor($selfcal_dim->[0]/$selfcal->{"spacing"}+1),
			"ny" => floor($selfcal_dim->[1]/$selfcal->{"spacing"}+1),
			"cen" => $sensor_cen,
			"rot"=> $ip_rot->{$sen_i,$sen_j},
			"outer_loop_y" => 0, 
			"lat_offset"   => $lat_offset->{$sen_i,$sen_j},
			"label"        => "SELFCAL_"."S".$sen_i.$sen_j};
	    }
	}
    } else {
	# corner raft case
	# first the two guide sensors
	foreach my $gs_ix (0..1) {
	    my @gs_cen=(60.338,13.838);
	    $sensor_cen=($gs_ix==0)?[$gs_cen[0],$gs_cen[1]]:[$gs_cen[1],$gs_cen[0]];
	    my $sspec={"x" => [-$gs_sensor_dim->[0]/2.0,+$gs_sensor_dim->[0]/2],
		       "y" => [-$gs_sensor_dim->[1]/2.0,+$gs_sensor_dim->[1]/2.0],
		       "nx" => floor($gs_sensor_dim->[0]/$samp->[0]+1),
		       "ny" => floor($gs_sensor_dim->[1]/$samp->[1]+1),
		       "cen" => $sensor_cen,
		       "rot"=> $gs_ip_rot->{$gs_ix},
		       "outer_loop_y"=> $gs_ix%2,
		       "lat_offset"  => $gs_lat_offset->{$gs_ix},
		       "label"       => "GS".$gs_ix};
	    push(@{$scanspec_sensors},$sspec);

	    my $scspec={"x" => [$selfcal->{"sensor"}->[0]->[0],$selfcal->{"sensor"}->[1]->[0]],
		    "y" => [$selfcal->{"sensor"}->[0]->[1],$selfcal->{"sensor"}->[1]->[1]],
		    "nx" => floor($selfcal_dim->[0]/$selfcal->{"spacing"}+1),
		    "ny" => floor($selfcal_dim->[1]/$selfcal->{"spacing"}+1),
		    "cen" => $sensor_cen,
		    "rot"=> $gs_ip_rot->{$gs_ix},
		    "outer_loop_y" => 1, # outer loop spec needs to be coordinated with selfcal definition
		    "lat_offset"   => $gs_lat_offset->{$gs_ix},
		    "label"        => "SELFCAL_"."GS".$gs_ix};
	    push(@{$selfcal_spec_sensors},$scspec);
	}
	foreach my $wfs_ix (0..1) {
	    $sensor_cen=[15.850,4.225+$wfs_ix*(27.475-4.225)];
	    my $transverse_step=($wfs_ix-0.5)*3.0*sin(8.5*atan2(1,1)/45.0);
	    my $sspec={"x" => [-$wfs_sensor_dim->[0]/2.0+$transverse_step,
			       +$wfs_sensor_dim->[0]/2.0+$transverse_step],
		       "y" => [-$wfs_sensor_dim->[1]/2.0,+$wfs_sensor_dim->[1]/2.0],
		       "nx" => floor($wfs_sensor_dim->[0]/$samp->[0]+1),
		       "ny" => floor($wfs_sensor_dim->[1]/$samp->[1]+1),
		       "cen" => $sensor_cen,
		       "rot"=> $gs_ip_rot->{$wfs_ix},
		       "outer_loop_y"=> $wfs_ix%2,
		       "lat_offset"  => $wfs_lat_offset->{$wfs_ix},
		       "label"       => "WFS".$wfs_ix};
	    push(@{$scanspec_sensors},$sspec);
	    my $scspec={"x" => [$selfcal->{"sensor"}->[0]->[0]+$transverse_step,
				$selfcal->{"sensor"}->[1]->[0]+$transverse_step],
		    "y" => [$selfcal->{"sensor"}->[0]->[1],$selfcal->{"sensor"}->[1]->[1]],
		    "nx" => floor($selfcal_dim->[0]/$selfcal->{"spacing"}+1),
		    "ny" => floor($selfcal_dim->[1]/$selfcal->{"spacing"}+1),
		    "cen" => $sensor_cen,
		    "rot"=> $wfs_ip_rot->{$wfs_ix},
		    "outer_loop_y" => 1, # outer loop spec needs to be coordinated with selfcal definition
		    "lat_offset"   => $wfs_lat_offset->{$wfs_ix},
		    "label"        => "SELFCAL_"."WFS".$wfs_ix};
	    push(@{$selfcal_spec_sensors},$scspec);
	}
    }
    
    my $scanspec_rereference=[];

    foreach my $i (0..$#{$reref_cen}) {
	$scanspec_rereference->[$i]={"x" => [0,0],
				 "y" => [0,0],
				 "nx" => 1,
				 "ny" => 1,
				 "cen" => $reref_cen->[$i],
				 "rot" => 0,
				 "outer_loop_y" => 0,
				 "lat_offset"   => [0,0],
				 "label"        => "REREF"};
    }
    return( [ $scanspec_sensors,$scanspec_fiducial,
	      $scanspec_rereference,
	      $selfcal_spec_fiducial,$selfcal_spec_sensors ] );
}

sub sample_reference {
    my ($slist)=@_;
    my $ret="";
    if ($#{$slist}) {
	$ret .= sprintf("! part of label %s\n","REREF");
	foreach my $sl_ix (0..$#{$slist}) {
	    foreach my $cl (@{$slist->[$sl_ix]->{"scan"}}) {
		$ret .= sprintf("%s\n",join(' ',@{$cl}));
	    }
	}
    }
    $ret;
}

sub sample_selfcal {
    my ($slist)=@_;
    my $ret="";
    if ($#{$slist}) {
	foreach my $sl_ix (0..$#{$slist}) {
	    $ret .= sprintf("! part of label %s\n",$slist->[$sl_ix]->{"label"});
	    my @scanlist = @{$slist->[$sl_ix]->{"scan"}};
	    my $do_step=0;
	    if (! $do_step) {
		# prepares scan delimeters
		$ret .= sprintf("! SCAN n=%d dc=%f\n",$#scanlist-$[+1,0.95);
		foreach my $i (0,$#scanlist) {
		    $ret .= sprintf("%g %g\n",@{$scanlist[$i]});
		}
		# $n_scan_samples += ($#scanlist-$[+1);
	    } else {
		foreach my $i (0..$#scanlist) {
		    $ret .= sprintf("%g %g\n",@{$scanlist[$i]});
		    # $n_scan_samples++;
		}
	    }
	    if (0) {
		my @cl=@{$slist->[$sl_ix]->{"scan"}};
		foreach my $cls (@cl[0,$#cl]) {
		    $ret .= sprintf("%s\n",join(' ',@{$cls}));
		}
	    }
	}
    }
    $ret;
}

sub retrieve_opts {
    my ($filename)=@_;
    my $pars={};
    open(OPT,"<",$filename) || die "can't open options file $filename..\n";
    while (my $line=<OPT>) {
	next if ($line =~ /^#/);
	chomp $line;
	$line =~ tr /=/ /;
	my @entry=split(' ',$line);
	my $value=$entry[$#entry];
	$pars->{$entry[0]}=$value;
    }
    close(OPT);
    $pars;
}
