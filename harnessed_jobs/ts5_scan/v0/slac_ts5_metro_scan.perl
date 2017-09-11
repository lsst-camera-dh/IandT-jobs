#!/usr/bin/perl
use strict;
use warnings;
use POSIX;
use Getopt::Long;

my $raft_os=[9.01,-19.105]; # millimeters
my $raft_theta=0.173;    # degrees (checked against sense of stage x,y)
my ($include_sensors,$include_reref,$include_fiducials)=(1,1,1);
my ($sensor_step_sample,$fiducial_step_sample)=(0,0);
my $reref_cen=[[-55,-15-42.5],[0,+15+42.5],[55,-15-42.5]];
my $sensor_dim=[41.0,41.0];

my $usage="usage:\n".
    "$0 [args] > <plan_file>\n".
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
    "\t[--help]\n";

my ($raft_center_x,$raft_center_y,$raft_rotation,
    $exclude_sensors,$exclude_reref,$exclude_fiducials,
    $these_sensors,$report_corners,
    $fiducial_sample_spacing,$sensor_sample_spacing,
    $samples_betw_reref);

($fiducial_sample_spacing,$sensor_sample_spacing)=(1,1);
$samples_betw_reref=160;
my @reref_coords;
my $rerefcoords;
my @do_sensors;
my $help=0;

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
	   "help"            => \$help) ||
    die("Error in command line arguments! exiting..\n".$usage);
if (@ARGV) {
    printf STDERR "left over command line entries: %s\n",join(' ',@ARGV);
    die($usage);
}

if ($help) {
    die($usage);
}

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
print STDERR $str;

if (($include_fiducials==0) && 
    (($include_sensors==0) && (! @do_sensors))) {
    printf STDERR "wait .. nothing to measure, what's the point of rereferencing??\nexiting..\n";
    exit(1);
}

##################################################################
# PROCEED WITH SCAN PLAN GENERATION
##################################################################

printf "! TF X0=%f\n",$raft_os->[0];
printf "! TF Y0=%f\n",$raft_os->[1];
printf "! TF theta=%f\n",$raft_theta;

my $ss=get_scanspecs();

if (defined($report_corners)) {
    # go through the label and report. Then exit.
    my %n_by_label=("fid0" => 2,"fid1" => 2,
		    "S00"  => 1,"S02"  => 1,"S20"  => 1,"S22"  => 1,
		    "S01"  => 0,"S21"  => 0,"S10"  => 0,"S12"  => 0,"S11"  => 0,
		    "REREF"=> 0);
    
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
    exit;
}

my $scl=[];
my $reref=[];
my $lbl=[];

foreach my $ssv (@{$ss}) { # loop over scan types
    foreach my $ix0 (sort keys @{$ssv}) { # loop over unique labels
	if (! $include_fiducials) {
	    next if ($ssv->[$ix0]->{"label"} =~ /fid/);
	}

	if ((! $include_sensors) && 
	    ($ssv->[$ix0]->{"label"} =~ /^S\d\d/)) {
	    # and look for a match in @do_sensors (if defined)
	    if (@do_sensors) {
		my $match_found=0;
		foreach my $ds (@do_sensors) {
		    $match_found=1 if ($ssv->[$ix0]->{"label"} =~ /$ds/);
		}
		next if (!$match_found);
	    } else {
		next if ($ssv->[$ix0]->{"label"} =~ /S\d\d/);
	    }
	}

	my $scan_lists=expand_scan($ssv->[$ix0],$raft_os,$raft_theta);
	if ($ssv->[$ix0]->{"label"} =~ /REREF/) {
	    # divert the rereference to a different list
	    push(@{$reref},$scan_lists);
	    printf STDERR "REREF label: %s\n",$ssv->[$ix0]{"label"};
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

my $next_scan_ix=0;
my ($start,$stop);
my $total_scan_distance=0;
my $step_number=0;
my $prev_coords;
my $n_scan_samples=0;

if ($include_reref) {
    printf "%s",sample_reference($reref_scan_list);
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
    printf "! part of label %s\n",$lbl;
    my $do_step=0;
    $do_step=1 if ((($lbl =~ /^S\d\d/) &&   ($sensor_step_sample==1))|| 
		   (($lbl =~ /^fid\d/) && ($fiducial_step_sample==1)));

    if (! $do_step) {
	# prepares scan delimeters
	printf "! SCAN n=%d dc=%f\n",$#scanlist-$[+1,0.95;
	foreach my $i (0,$#scanlist) {
	    printf "%g %g\n",@{$scanlist[$i]};
	}
	$n_scan_samples += ($#scanlist-$[+1);
    } else { # prepares a visit list
	foreach my $i (0..$#scanlist) {
	    printf "%g %g\n",@{$scanlist[$i]};
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
	    printf "%s",sample_reference($reref_scan_list);
	}
#	printf "no no\n";
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
    printf "%s",sample_reference($reref_scan_list);
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
    my $samp=[1,1];
    $samp=[$fiducial_sample_spacing,
	   $fiducial_sample_spacing];
    my $fid_cen;
    my $raft_cen=[30,-40];
    $raft_cen=[0,0];
    my $fid_x_offset=(190-12.7)/2.0;
    my $lat_offset={};
    my $ip_rot={};
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

    my $scanspec_fiducial=[];
    $fid_cen=[$raft_cen->[0]-$fid_x_offset,$raft_cen->[1]];
    $scanspec_fiducial->[0]={"x" => [-$fid_dim->[0]/2.0,+$fid_dim->[0]/2.0],
				 "y" => [$fid_cen->[1]-$fid_dim->[1]/2.0,
					 $fid_cen->[1]+$fid_dim->[1]/2.0],
				 "nx" => floor($fid_dim->[0]/$samp->[0]+1),
				 "ny" => floor($fid_dim->[1]/$samp->[1]+1),
				 "cen" => $fid_cen,
				 "rot"=> 0,
				 "lat_offset" => [0,0],
				 "outer_loop_y" => 0,
				 "label" => "fid0"};
    $fid_cen=[$raft_cen->[0]+$fid_x_offset,$raft_cen->[1]];
    $scanspec_fiducial->[1]={"x" => [-$fid_dim->[0]/2.0,+$fid_dim->[0]/2.0],
				 "y" => [-$fid_dim->[1]/2.0,+$fid_dim->[1]/2.0],
				 "nx" => floor($fid_dim->[0]/$samp->[0]+1),
				 "ny" => floor($fid_dim->[1]/$samp->[1]+1),
				 "cen" => $fid_cen,
				 "rot"=> 0,
				 "lat_offset" => [0,0],
				 "outer_loop_y" => 1,
				 "label" => "fid1"};
    # move onto sensors
    $samp=[1,1];
    $samp=[$sensor_sample_spacing,
	   $sensor_sample_spacing];
    my $sensor_cen;
    my $scanspec_sensors=[];

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
	}
    }
    my $scanspec_rereference=[];

    # if (0) {
    # 	# this reref is for positions on the fiducials
    # 	$reref_cen=[[$scanspec_fiducial->[0]->{"cen"}->[0]+3,-30],
    # 		    [$scanspec_fiducial->[0]->{"cen"}->[0]+3,+30],
    # 		    [$scanspec_fiducial->[1]->{"cen"}->[0]-3,
    # 		     $scanspec_fiducial->[1]->{"cen"}->[1]]];
    # }

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
    return( [ $scanspec_sensors,$scanspec_fiducial,$scanspec_rereference ] );
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
#	$ret .= "no no\n";
    }
    $ret;
}
